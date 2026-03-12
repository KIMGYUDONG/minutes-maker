"""Streamlit UI for the meeting minutes service."""

import sys
import streamlit as st
from pathlib import Path
import traceback
from datetime import datetime
import threading
import time

from config import Config
from utils import validate_audio_file, format_error_message
from audio_processor import AudioProcessor
from llm_processor import LLMProcessor
from notion_integration import NotionClient
from telegram_notify import send_telegram_notification

# Module-level worker registry (survives Streamlit reruns, not serialized)
_active_workers: dict[str, threading.Thread] = {}


# Page configuration
st.set_page_config(
    page_title="Meeting Minutes Generator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1f77b4;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #2c3e50;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'transcript_result' not in st.session_state:
        st.session_state.transcript_result = None
    if 'meeting_minutes' not in st.session_state:
        st.session_state.meeting_minutes = None
    if 'notion_url' not in st.session_state:
        st.session_state.notion_url = None
    if 'processing_id' not in st.session_state:
        st.session_state.processing_id = None


def clear_previous_results():
    """Clear previous meeting results and widget states for new processing."""
    import time

    # Clear widget states for text_area fields from previous processing
    old_pid = st.session_state.processing_id
    if old_pid:
        widget_keys = [
            f'edit_summary_{old_pid}',
            f'edit_key_updates_{old_pid}',
            f'edit_discussion_{old_pid}',
            f'edit_action_items_{old_pid}'
        ]
        for key in widget_keys:
            if key in st.session_state:
                del st.session_state[key]

    # Generate new processing ID to force widget re-creation
    st.session_state.processing_id = str(int(time.time() * 1000))

    # Clear previous results
    st.session_state.transcript_result = None
    st.session_state.meeting_minutes = None
    st.session_state.notion_url = None


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

    status_text.info("⏳ Transcript 파일 로드 중...")
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
    status_text.info("⏳ Generating meeting minutes with Gemini...")
    progress_bar.progress(0.6)

    llm_processor = LLMProcessor()

    try:
        minutes = llm_processor.create_meeting_minutes(
            transcript=transcript_text,
            manual_notes=manual_notes if manual_notes.strip() else None
        )

        st.session_state.meeting_minutes = minutes

        # 자동 노션 저장
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

        # 텔레그램 알림
        status_text.info("⏳ 텔레그램 알림 전송 중...")
        progress_bar.progress(0.9)
        send_telegram_notification(url)

        progress_bar.progress(1.0)
        status_text.success("✅ 회의록이 노션에 저장되었습니다!")
        progress_bar.empty()

        st.rerun()

    except Exception as llm_error:
        progress_bar.empty()
        st.warning("⚠️ LLM 처리 실패")
        st.error(format_error_message(llm_error))
        st.error("**Details:**")
        st.code(traceback.format_exc())


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
        st.markdown("### 📋 Meeting Minutes Generator")
        st.markdown("---")

        # Demo mode banner
        if Config.DEMO_MODE:
            st.warning("🎭 **Demo Mode**")
            st.caption("Processing is disabled in demo environment.")
            st.markdown("---")

        st.markdown("#### ℹ️ How to Use")
        st.markdown("""
        1. **Upload Audio**: Upload your meeting recording (m4a, mp3, or wav)
        2. **Add Notes**: Optionally add manual notes
        3. **Process**: Click 'Generate Minutes'
        4. **Edit**: Review and edit the output
        5. **Send**: Click 'Send to Notion'
        """)

        st.markdown("---")
        st.markdown("#### ⚙️ System Info")

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

    st.markdown('<div class="main-header">📋 Automated Meeting Minutes</div>', unsafe_allow_html=True)
    st.markdown("Transform your meeting recordings into structured minutes with AI")

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
        st.markdown('<div class="section-header">📁 File Upload</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload audio or transcript file",
            type=[fmt.lstrip('.') for fmt in Config.ALL_UPLOAD_FORMATS],
            help=f"Audio: {', '.join(Config.SUPPORTED_FORMATS)} | Transcript: {', '.join(Config.TEXT_FORMATS)}"
        )

        if uploaded_file:
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.info(f"📁 {uploaded_file.name} ({file_size_mb:.1f} MB)")

    with col2:
        st.markdown('<div class="section-header">📝 Manual Notes (Optional)</div>', unsafe_allow_html=True)
        manual_notes = st.text_area(
            "Add your manual notes here",
            height=200,
            placeholder="Paste or type any manual notes you took during the meeting...",
            help="These notes will be merged with the audio transcript"
        )

    st.markdown("---")

    if uploaded_file:
        if st.button("🚀 Generate Meeting Minutes", type="primary", use_container_width=True):
            if Config.DEMO_MODE:
                st.warning(
                    "🎭 **Demo Mode Active** - "
                    "Processing is disabled in this environment. "
                    "In production, this would transcribe the audio and generate meeting minutes."
                )
            else:
                process_meeting(uploaded_file, manual_notes)
    else:
        st.info("👆 Please upload an audio or transcript file to get started")

    # Active processing: show polling UI
    worker_id = st.session_state.get("worker_id")
    if worker_id and st.session_state.get("progress_state"):
        state = st.session_state.progress_state

        if state["status"] == "done":
            # Transfer results to session state and cleanup
            st.session_state.meeting_minutes = state.get("minutes")
            st.session_state.notion_url = state.get("notion_url")
            st.session_state.worker_id = None
            _active_workers.pop(worker_id, None)
            st.rerun()

        elif state["status"] == "error":
            st.error(f"❌ {state['error']}")
            if state.get("transcript_path"):
                st.info(f"📁 Transcript 저장됨: `{state['transcript_path']}`")
            st.session_state.worker_id = None
            _active_workers.pop(worker_id, None)

        else:
            # Running: show progress and poll
            st.progress(state["progress"])
            status_text = st.empty()
            status_text.info(f"⏳ {state['message']}")

            # Safety check: thread alive?
            thread = _active_workers.get(worker_id)
            if thread and not thread.is_alive() and state["status"] == "running":
                st.error("Processing failed unexpectedly. Check server logs.")
                st.session_state.worker_id = None
                _active_workers.pop(worker_id, None)
            else:
                poll_interval = 5 if state["progress"] < 0.5 else 1
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
        st.error("**Details:**")
        st.code(traceback.format_exc())


def process_audio_file(uploaded_file, manual_notes: str):
    """Start audio processing in background thread."""
    upload_path = Config.UPLOAD_DIR / uploaded_file.name
    with open(upload_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    is_valid, error_msg = validate_audio_file(upload_path)
    if not is_valid:
        st.error(f"❌ {error_msg}")
        return

    # Capture values before thread start (UploadedFile may become invalid after rerun)
    file_name = uploaded_file.name
    notes_text = manual_notes.strip() if manual_notes else ""

    # Shared progress state (dict, thread-safe for simple read/write via GIL)
    progress_state = {
        "phase": "whisper",
        "message": "Initializing audio processor...",
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

            audio_processor = AudioProcessor(progress_callback=update_fn)
            transcript_result = audio_processor.transcribe(upload_path)

            print(f"[DEBUG] === 오디오 처리 완료 ==="); sys.stdout.flush()
            audio_processor.cleanup()

            if not transcript_result.get('text'):
                progress_state["error"] = "No speech detected"
                progress_state["status"] = "error"
                return

            # Save transcript immediately (uses captured file_name, not uploaded_file)
            saved_path = save_transcript(transcript_result['text'], file_name)
            progress_state["transcript_path"] = saved_path
            print(f"[DEBUG] 전사 결과 저장 완료 → {saved_path}"); sys.stdout.flush()

            # Phase: LLM
            progress_state["phase"] = "llm"
            progress_state["message"] = "Generating meeting minutes with Gemini Pro..."
            progress_state["progress"] = 0.6
            llm_processor = LLMProcessor()
            minutes = llm_processor.create_meeting_minutes(
                transcript=transcript_result['text'],
                manual_notes=notes_text if notes_text else None
            )
            progress_state["minutes"] = minutes
            print(f"[DEBUG] Gemini API 완료"); sys.stdout.flush()

            # Phase: Notion
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
            send_telegram_notification(url)
            print(f"[DEBUG] 텔레그램 완료"); sys.stdout.flush()

            # Done - set status="done" LAST (polling UI trigger)
            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "완료!"
            progress_state["status"] = "done"
            print(f"[DEBUG] === 전체 파이프라인 완료 ==="); sys.stdout.flush()

        except Exception as e:
            print(f"[DEBUG] ❌ 파이프라인 예외: {type(e).__name__}: {e}"); sys.stdout.flush()
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
    _active_workers[worker_id] = thread
    thread.start()
    st.rerun()


def display_results():
    """Display completion message after auto-save to Notion."""
    st.markdown("---")
    st.markdown('<div class="section-header">✅ 완료</div>', unsafe_allow_html=True)

    st.success("회의록이 노션에 자동 저장되었습니다!")

    if st.session_state.notion_url:
        st.markdown(f"### 📎 [노션에서 보기]({st.session_state.notion_url})")

    st.info("💡 터미널에서 `cd bridge && claude` 실행 후 `/linear` 입력하여 Linear 이슈를 등록하세요")


if __name__ == "__main__":
    main()
