"""Soomgo Client Meeting Minutes Page."""

import streamlit as st
from pathlib import Path
import threading
import time

from config import Config
from utils import validate_audio_file
from whisper_client import WhisperClient
from llm_processor import LLMProcessor
from notion_integration import NotionClient
from telegram_notify import send_telegram_notification_to_user
from worker_registry import active_workers


def main():
    # Initialize session state
    for key in ["soomgo_worker_id", "soomgo_progress_state", "soomgo_minutes",
                "soomgo_metadata", "soomgo_notion_url", "soomgo_telegram_warning"]:
        if key not in st.session_state:
            st.session_state[key] = None

    st.markdown(
        '<div class="main-header">🤝 숨고 클라이언트 회의록</div>',
        unsafe_allow_html=True,
    )
    st.markdown("영업 미팅 녹음을 업로드하면 자동으로 회의록을 생성합니다.")

    if Config.DEMO_MODE:
        st.info("🎭 Demo Mode - 처리가 비활성화되어 있습니다.")
        st.stop()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            '<div class="section-header">📁 파일 업로드</div>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "음성 또는 텍스트 파일",
            type=[fmt.lstrip(".") for fmt in Config.ALL_UPLOAD_FORMATS],
            help=f"Audio: {', '.join(Config.SUPPORTED_FORMATS)} | Text: {', '.join(Config.TEXT_FORMATS)}",
            key="soomgo_uploader",
        )
        if uploaded_file:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📁 {uploaded_file.name} ({file_size_mb:.1f} MB)")

    with col2:
        st.markdown(
            '<div class="section-header">📝 미팅 정보</div>',
            unsafe_allow_html=True,
        )
        client_name = st.text_input(
            "클라이언트명 *", placeholder="예: F&B 프랜차이즈"
        )
        meeting_type = st.selectbox(
            "미팅 유형", ["초기 상담", "후속 미팅", "계약 미팅"]
        )
        industry = st.selectbox("업종", [
            "IT/소프트웨어", "F&B/외식", "숙박/관광", "제조/생산",
            "유통/물류", "교육", "의료/헬스케어", "부동산/건설", "뷰티/패션", "기타"
        ])
        user_name = st.selectbox(
            "담당자", list(Config.TELEGRAM_USERS.keys())
        )
        manual_notes = st.text_area(
            "수기 노트 (선택)",
            height=120,
            placeholder="미팅 중 메모한 내용...",
            key="soomgo_notes",
        )

    st.markdown("---")

    if uploaded_file and client_name:
        if st.button(
            "🚀 회의록 생성", type="primary", use_container_width=True, key="soomgo_generate"
        ):
            process_soomgo_meeting(
                uploaded_file,
                client_name,
                meeting_type,
                industry,
                user_name,
                manual_notes,
            )
    elif uploaded_file:
        st.warning("👆 클라이언트명을 입력해주세요.")
    else:
        st.info("👆 음성 파일을 업로드하고 미팅 정보를 입력하세요.")

    # Active processing: show polling UI
    worker_id = st.session_state.get("soomgo_worker_id")
    if worker_id and st.session_state.get("soomgo_progress_state"):
        state = st.session_state.soomgo_progress_state

        if state["status"] == "done":
            st.session_state.soomgo_notion_url = state.get("notion_url")
            if state.get("telegram_warning"):
                st.session_state.soomgo_telegram_warning = True
            st.session_state.soomgo_worker_id = None
            active_workers.pop(worker_id, None)
            st.rerun()

        elif state["status"] == "error":
            st.error(f"❌ {state['error']}")
            st.session_state.soomgo_worker_id = None
            active_workers.pop(worker_id, None)

        else:
            st.progress(state["progress"])
            status_text = st.empty()
            status_text.info(f"⏳ {state['message']}")

            if st.button("❌ 취소", key="cancel_soomgo"):
                state["status"] = "cancelled"
                st.session_state.soomgo_worker_id = None
                active_workers.pop(worker_id, None)
                st.warning("처리가 취소되었습니다.")
                st.rerun()
                return

            thread = active_workers.get(worker_id)
            if thread and not thread.is_alive() and state["status"] == "running":
                st.error("처리 중 예기치 않은 오류가 발생했습니다.")
                st.session_state.soomgo_worker_id = None
                active_workers.pop(worker_id, None)
            else:
                poll_interval = 3 if state["progress"] < 0.5 else 1
                time.sleep(poll_interval)
                st.rerun()

    elif st.session_state.get("soomgo_notion_url"):
        display_soomgo_results()


def process_soomgo_meeting(
    uploaded_file, client_name, meeting_type, industry, user_name, manual_notes
):
    """Start Soomgo processing in background thread."""
    Config.setup_directories()
    upload_path = Config.UPLOAD_DIR / uploaded_file.name
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_ext = Path(uploaded_file.name).suffix.lower()

    # Pre-flight health check (audio only, not txt)
    if file_ext not in Config.TEXT_FORMATS:
        try:
            whisper = WhisperClient()
            whisper.health_check()
        except Exception as e:
            st.error(f"❌ Whisper 서버에 연결할 수 없습니다: {e}")
            st.info("서버 상태를 확인한 후 다시 시도해주세요.")
            upload_path.unlink(missing_ok=True)
            return

    # Capture values before thread start (UploadedFile becomes invalid after st.rerun)
    file_name = uploaded_file.name
    notes_text = manual_notes.strip() if manual_notes else ""

    progress_state = {
        "phase": "init",
        "message": "초기화 중...",
        "progress": 0.1,
        "status": "running",  # running | done | error | cancelled
        "minutes": None,
        "notion_url": None,
        "error": None,
        "metadata": {
            "client_name": client_name,
            "meeting_type": meeting_type,
            "industry": industry,
            "user_name": user_name,
        },
    }

    worker_id = str(int(time.time() * 1000))
    st.session_state.soomgo_progress_state = progress_state
    st.session_state.soomgo_worker_id = worker_id

    def background_work():
        try:
            # 1. Transcribe
            if file_ext in Config.TEXT_FORMATS:
                progress_state["message"] = "텍스트 파일 로드 중..."
                progress_state["progress"] = 0.3
                transcript_text = Path(upload_path).read_text(encoding="utf-8")
            else:
                is_valid, error_msg = validate_audio_file(upload_path)
                if not is_valid:
                    progress_state["error"] = error_msg
                    progress_state["status"] = "error"
                    return

                progress_state["message"] = "Whisper 서버에 연결 중..."
                progress_state["progress"] = 0.1

                def update_fn(msg):
                    progress_state["message"] = msg

                client = WhisperClient(progress_callback=update_fn)
                result = client.transcribe(upload_path)
                transcript_text = result["text"]
                progress_state["progress"] = 0.4

            if not transcript_text.strip():
                progress_state["error"] = "음성이 감지되지 않았습니다."
                progress_state["status"] = "error"
                return

            # Check cancellation before LLM
            if progress_state.get("status") == "cancelled":
                return

            # Save transcript backup
            transcript_path = Config.UPLOAD_DIR / f"{Path(file_name).stem}_transcript.txt"
            transcript_path.write_text(transcript_text, encoding="utf-8")

            # 2. LLM
            progress_state["phase"] = "llm"
            progress_state["message"] = "Gemini로 회의록 생성 중..."
            progress_state["progress"] = 0.5
            llm = LLMProcessor()
            minutes = llm.create_sales_meeting_minutes(
                transcript=transcript_text,
                client_name=client_name,
                manual_notes=notes_text if notes_text else None,
            )
            progress_state["minutes"] = minutes

            # Phase: Notion
            if progress_state.get("status") == "cancelled":
                return
            progress_state["phase"] = "notion"
            progress_state["message"] = "노션에 저장 중..."
            progress_state["progress"] = 0.7
            notion = NotionClient()
            url = notion.create_soomgo_minutes(
                content=minutes["content"],
                client_name=client_name,
                meeting_type=meeting_type,
                industry=industry,
                user_name=user_name,
                ai_summary=minutes.get("ai_summary", ""),
            )
            progress_state["notion_url"] = url

            # Phase: Telegram
            progress_state["phase"] = "telegram"
            progress_state["message"] = "텔레그램 알림 전송 중..."
            progress_state["progress"] = 0.9
            telegram_ok = send_telegram_notification_to_user(
                user_name=user_name, notion_url=url, client_name=client_name,
            )
            if not telegram_ok:
                progress_state["telegram_warning"] = True

            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "완료!"
            progress_state["status"] = "done"

        except Exception as e:
            if progress_state.get("status") == "cancelled":
                return
            print(f"[ERROR] Soomgo pipeline: {type(e).__name__}: {e}")
            progress_state["error"] = str(e)
            progress_state["status"] = "error"
            upload_path.unlink(missing_ok=True)

    thread = threading.Thread(target=background_work, daemon=True)
    active_workers[worker_id] = thread
    thread.start()
    st.rerun()


def display_soomgo_results():
    """Display completion message after auto-save to Notion."""
    st.markdown("---")
    st.markdown('<div class="section-header">✅ 완료</div>', unsafe_allow_html=True)
    st.success("회의록이 노션에 저장되었습니다!")
    st.markdown(f"### 📎 [노션에서 보기]({st.session_state.soomgo_notion_url})")
    if st.session_state.get("soomgo_telegram_warning"):
        st.warning("⚠️ 텔레그램 알림 전송에 실패했습니다. 수동으로 공유해주세요.")


main()
