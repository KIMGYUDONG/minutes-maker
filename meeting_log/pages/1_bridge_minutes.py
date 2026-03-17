"""Bridge 회의록 - Team meeting recording to minutes."""

import sys
import streamlit as st
from pathlib import Path
import traceback
from datetime import datetime
import threading
import time

from config import Config
from utils import validate_audio_file, format_error_message
try:
    from audio_processor import AudioProcessor
    HAS_LOCAL_WHISPER = True
except ImportError:
    HAS_LOCAL_WHISPER = False
from llm_processor import LLMProcessor
from notion_integration import NotionClient
from telegram_notify import send_telegram_notification
from worker_registry import active_workers


def initialize_session_state():
    """Initialize session state variables."""
    if 'transcript_result' not in st.session_state:
        st.session_state.transcript_result = None
    if 'meeting_minutes' not in st.session_state:
        st.session_state.meeting_minutes = None
    if 'notion_url' not in st.session_state:
        st.session_state.notion_url = None


def clear_previous_results():
    """Clear previous meeting results for new processing."""
    st.session_state.transcript_result = None
    st.session_state.meeting_minutes = None
    st.session_state.notion_url = None
    st.session_state.telegram_warning = False


def save_transcript(transcript_text: str, original_filename: str) -> str:
    """Save transcript to file for preservation.

    Args:
        transcript_text: The transcribed text from audio
        original_filename: Original audio filename for naming

    Returns:
        str: Path to the saved transcript file
    """
    base_name = Path(original_filename).stem
    output_path = Config.UPLOAD_DIR / f"{base_name}_transcript.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(transcript_text)

    return str(output_path)


def process_transcript_file(uploaded_file, manual_notes: str):
    """Process uploaded transcript txt file directly (skip Whisper)."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.info("⏳ 텍스트 파일 로드 중...")
    progress_bar.progress(0.3)

    # Read txt file directly
    transcript_text = uploaded_file.read().decode('utf-8')

    if not transcript_text.strip():
        progress_bar.empty()
        st.warning("⚠️ 빈 파일입니다")
        return

    print(f"[DEBUG] === Transcript 파일 로드 완료 ===")
    print(f"[DEBUG] 텍스트 길이: {len(transcript_text)} 문자")

    st.session_state.transcript_result = {
        'text': transcript_text,
        'segments': [],
        'source': 'txt_upload'
    }

    # LLM processing
    status_text.info("⏳ Gemini로 회의록 생성 중...")
    progress_bar.progress(0.6)

    llm_processor = LLMProcessor()

    try:
        minutes = llm_processor.create_meeting_minutes(
            transcript=transcript_text,
            manual_notes=manual_notes if manual_notes.strip() else None
        )

        st.session_state.meeting_minutes = minutes

        # Auto-save to Notion
        status_text.info("⏳ 노션에 저장 중...")
        progress_bar.progress(0.8)
        notion_client = NotionClient()
        url = notion_client.create_meeting_minutes(
            summary=minutes.get('summary', ''),
            key_updates=minutes.get('key_updates', ''),
            discussion_log=minutes.get('discussion_log', ''),
            action_items=minutes.get('action_items', '')
        )
        st.session_state.notion_url = url

        # Telegram notification
        status_text.info("⏳ 텔레그램 알림 전송 중...")
        progress_bar.progress(0.9)
        telegram_ok = send_telegram_notification(url)
        if not telegram_ok:
            st.session_state.telegram_warning = True

        progress_bar.progress(1.0)
        status_text.success("✅ 회의록이 노션에 저장되었습니다!")
        progress_bar.empty()
        st.rerun()

    except Exception as llm_error:
        progress_bar.empty()
        st.warning("⚠️ LLM 처리 실패")
        st.error(format_error_message(llm_error))
        print(f"[ERROR] LLM processing failed:\n{traceback.format_exc()}")


def validate_configuration():
    """Validate configuration and show errors if any."""
    errors = Config.validate()
    if errors:
        st.error("⚠️ Configuration Error")
        for error in errors:
            st.error(f"- {error}")
        st.info("Please create a `.env` file based on `.env.example` and fill in your API keys.")
        st.stop()


def show_sidebar():
    """Display sidebar with information and settings."""
    with st.sidebar:
        st.markdown("### 📋 회의록 생성기")
        st.markdown("---")

        # Demo mode banner
        if Config.DEMO_MODE:
            st.warning("🎭 **Demo Mode**")
            st.caption("Processing is disabled in demo environment.")
            st.markdown("---")

        st.markdown("#### ℹ️ 사용 방법")
        st.markdown("""
        1. **파일 업로드**: 회의 녹음 파일(m4a, mp3, wav) 또는 텍스트 파일(txt) 업로드
        2. **노트 추가**: 수기 노트 입력 (선택)
        3. **생성**: '회의록 생성' 클릭
        4. **확인**: AI 생성 결과 검토
        5. **저장**: '노션에 저장' 클릭
        """)

        st.markdown("---")
        st.markdown("#### ⚙️ 시스템 정보")

        if Config.DEMO_MODE:
            st.info("Demo environment - GPU info not available")
        else:
            try:
                import torch
                if torch.cuda.is_available():
                    st.success(f"✅ GPU: {torch.cuda.get_device_name(0)}")
                    st.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
                else:
                    st.warning("⚠️ GPU not available")
            except ImportError:
                st.warning("⚠️ PyTorch not installed")

        st.markdown(f"**Model**: {Config.WHISPER_MODEL}")
        st.markdown(f"**Fallback**: {Config.WHISPER_FALLBACK_MODEL}")


def main():
    """Main application."""
    initialize_session_state()

    # Skip configuration validation in demo mode
    if not Config.DEMO_MODE:
        validate_configuration()
        Config.setup_directories()

    show_sidebar()

    st.markdown('<div class="main-header">📋 회의록 자동 생성</div>', unsafe_allow_html=True)
    st.markdown("회의 녹음을 AI로 구조화된 회의록으로 변환합니다")

    # Demo mode banner at top
    if Config.DEMO_MODE:
        st.info(
            "🎭 **Demo Environment** - "
            "This is a portfolio demonstration. "
            "File processing is disabled. "
            "See the screenshots for actual results."
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="section-header">📁 파일 업로드</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "음성 또는 텍스트 파일 업로드",
            type=[fmt.lstrip('.') for fmt in Config.ALL_UPLOAD_FORMATS],
            help=f"Audio: {', '.join(Config.SUPPORTED_FORMATS)} | Transcript: {', '.join(Config.TEXT_FORMATS)}"
        )

        if uploaded_file:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📁 {uploaded_file.name} ({file_size_mb:.1f} MB)")

    with col2:
        st.markdown('<div class="section-header">📝 수기 노트 (선택)</div>', unsafe_allow_html=True)
        manual_notes = st.text_area(
            "수기 노트 입력",
            height=200,
            placeholder="미팅 중 메모한 내용...",
            help="음성 전사와 합쳐져 회의록이 생성됩니다"
        )

    st.markdown("---")

    if uploaded_file:
        if st.button("🚀 회의록 생성", type="primary", use_container_width=True):
            if Config.DEMO_MODE:
                st.warning(
                    "🎭 **Demo Mode Active** - "
                    "Processing is disabled in this environment. "
                    "In production, this would transcribe the audio and generate meeting minutes."
                )
            else:
                process_meeting(uploaded_file, manual_notes)
    else:
        st.info("👆 음성 또는 텍스트 파일을 업로드하세요")

    # Active processing: show polling UI
    worker_id = st.session_state.get("worker_id")
    if worker_id and st.session_state.get("progress_state"):
        state = st.session_state.progress_state

        if state["status"] == "done":
            # Transfer results to session state and cleanup
            st.session_state.meeting_minutes = state.get("minutes")
            st.session_state.notion_url = state.get("notion_url")
            if state.get("telegram_warning"):
                st.session_state.telegram_warning = True
            st.session_state.worker_id = None
            active_workers.pop(worker_id, None)
            st.rerun()

        elif state["status"] == "error":
            st.error(f"❌ {state['error']}")
            if state.get("transcript_path"):
                st.warning(
                    f"💾 전사 결과가 저장되어 있습니다: `{state['transcript_path']}`\n\n"
                    "위 파일을 텍스트 파일(.txt)로 업로드하면 Whisper 단계를 건너뛰고 회의록을 생성할 수 있습니다."
                )
            st.session_state.worker_id = None
            active_workers.pop(worker_id, None)

        else:
            # Running: show progress and poll
            st.progress(state["progress"])
            status_text = st.empty()
            status_text.info(f"⏳ {state['message']}")

            if st.button("❌ 취소", key="cancel_bridge"):
                state["status"] = "cancelled"
                st.session_state.worker_id = None
                active_workers.pop(worker_id, None)
                st.warning("처리가 취소되었습니다.")
                if state.get("transcript_path"):
                    st.info(f"💾 전사 결과: `{state['transcript_path']}`")
                st.rerun()
                return

            # Safety check: thread alive?
            thread = active_workers.get(worker_id)
            if thread and not thread.is_alive() and state["status"] == "running":
                st.error("처리 중 예기치 않은 오류가 발생했습니다. 서버 로그를 확인하세요.")
                st.session_state.worker_id = None
                active_workers.pop(worker_id, None)
            else:
                poll_interval = 3 if state["progress"] < 0.5 else 1
                time.sleep(poll_interval)
                st.rerun()

    elif st.session_state.meeting_minutes:
        display_results()


def process_meeting(uploaded_file, manual_notes: str):
    """Route to appropriate processor based on file type."""
    clear_previous_results()

    file_ext = Path(uploaded_file.name).suffix.lower()

    try:
        if file_ext in Config.TEXT_FORMATS:
            # TXT file: skip Whisper, process directly
            process_transcript_file(uploaded_file, manual_notes)
        else:
            # Audio file: process with Whisper
            process_audio_file(uploaded_file, manual_notes)
    except Exception as e:
        st.error(format_error_message(e))
        print(f"[ERROR] Meeting processing failed:\n{traceback.format_exc()}")


def process_audio_file(uploaded_file, manual_notes: str):
    """Start audio processing in background thread."""
    upload_path = Config.UPLOAD_DIR / uploaded_file.name
    with open(upload_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    is_valid, error_msg = validate_audio_file(upload_path)
    if not is_valid:
        st.error(f"❌ {error_msg}")
        return

    # Pre-flight health check (only for remote Whisper)
    if not HAS_LOCAL_WHISPER:
        try:
            from whisper_client import WhisperClient
            whisper = WhisperClient()
            whisper.health_check()
        except Exception as e:
            st.error(f"❌ Whisper 서버에 연결할 수 없습니다: {e}")
            st.info("서버 상태를 확인한 후 다시 시도해주세요.")
            upload_path.unlink(missing_ok=True)
            return

    # Capture values before thread start (UploadedFile may become invalid after rerun)
    file_name = uploaded_file.name
    notes_text = manual_notes.strip() if manual_notes else ""

    # Shared progress state (dict, thread-safe for simple read/write via GIL)
    progress_state = {
        "phase": "whisper",
        "message": "오디오 프로세서 초기화 중...",
        "progress": 0.1,
        "status": "running",  # running | done | error
        "transcript_path": None,
        "notion_url": None,
        "minutes": None,
        "error": None,
    }

    worker_id = str(int(time.time() * 1000))
    st.session_state.progress_state = progress_state
    st.session_state.worker_id = worker_id

    def background_work():
        audio_processor = None
        try:
            def update_fn(msg):
                progress_state["message"] = msg

            # Phase: Whisper
            progress_state["phase"] = "whisper"
            progress_state["progress"] = 0.1
            print(f"[DEBUG] === 오디오 처리 시작 ===")
            print(f"[DEBUG] 파일 경로: {upload_path}")

            if HAS_LOCAL_WHISPER:
                audio_processor = AudioProcessor(progress_callback=update_fn)
                transcript_result = audio_processor.transcribe(upload_path)
                print(f"[DEBUG] === 오디오 처리 완료 ==="); sys.stdout.flush()
                audio_processor.cleanup()
            else:
                from whisper_client import WhisperClient
                whisper = WhisperClient(progress_callback=update_fn)
                transcript_result = whisper.transcribe(upload_path)
                print(f"[DEBUG] === Whisper HTTP 처리 완료 ==="); sys.stdout.flush()

            if not transcript_result.get('text'):
                progress_state["error"] = "음성이 감지되지 않았습니다"
                progress_state["status"] = "error"
                return

            # Save transcript immediately (uses captured file_name, not uploaded_file)
            saved_path = save_transcript(transcript_result['text'], file_name)
            progress_state["transcript_path"] = saved_path
            print(f"[DEBUG] 전사 결과 저장 완료 → {saved_path}"); sys.stdout.flush()

            # Check cancellation before LLM
            if progress_state.get("status") == "cancelled":
                return

            # Phase: LLM
            progress_state["phase"] = "llm"
            progress_state["message"] = "Gemini Pro로 회의록 생성 중..."
            progress_state["progress"] = 0.6
            llm_processor = LLMProcessor()
            minutes = llm_processor.create_meeting_minutes(
                transcript=transcript_result['text'],
                manual_notes=notes_text if notes_text else None
            )
            progress_state["minutes"] = minutes
            print(f"[DEBUG] Gemini API 완료"); sys.stdout.flush()

            # Phase: Notion
            if progress_state.get("status") == "cancelled":
                return
            progress_state["phase"] = "notion"
            progress_state["message"] = "노션에 저장 중..."
            progress_state["progress"] = 0.8
            notion_client = NotionClient()
            url = notion_client.create_meeting_minutes(
                summary=minutes.get('summary', ''),
                key_updates=minutes.get('key_updates', ''),
                discussion_log=minutes.get('discussion_log', ''),
                action_items=minutes.get('action_items', '')
            )
            progress_state["notion_url"] = url
            print(f"[DEBUG] Notion 저장 완료 → {url}"); sys.stdout.flush()

            # Phase: Telegram
            progress_state["phase"] = "telegram"
            progress_state["message"] = "텔레그램 알림 전송 중..."
            progress_state["progress"] = 0.9
            telegram_ok = send_telegram_notification(url)
            if not telegram_ok:
                progress_state["telegram_warning"] = True
            print(f"[DEBUG] 텔레그램 완료"); sys.stdout.flush()

            # Done
            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "완료!"
            progress_state["status"] = "done"
            print(f"[DEBUG] === 전체 파이프라인 완료 ==="); sys.stdout.flush()

        except Exception as e:
            if progress_state.get("status") == "cancelled":
                return
            print(f"[ERROR] Pipeline failed: {type(e).__name__}: {e}"); sys.stdout.flush()
            progress_state["error"] = str(e)
            progress_state["status"] = "error"
            upload_path.unlink(missing_ok=True)
        finally:
            try:
                if audio_processor:
                    audio_processor.cleanup()
            except Exception:
                pass

    thread = threading.Thread(target=background_work, daemon=True)
    active_workers[worker_id] = thread
    thread.start()
    st.rerun()


def display_results():
    """Display completion message after auto-save to Notion."""
    st.markdown("---")
    st.markdown('<div class="section-header">✅ 완료</div>', unsafe_allow_html=True)

    st.success("회의록이 노션에 자동 저장되었습니다!")

    if st.session_state.notion_url:
        st.markdown(f"### 📎 [노션에서 보기]({st.session_state.notion_url})")

    if st.session_state.get("telegram_warning"):
        st.warning("⚠️ 텔레그램 알림 전송에 실패했습니다. 수동으로 공유해주세요.")

    st.info("💡 회의록 확인 후 필요한 액션 아이템을 등록해주세요")


main()
