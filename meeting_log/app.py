"""Streamlit UI for the meeting minutes service."""

import streamlit as st
from pathlib import Path
import traceback
from datetime import datetime

from config import Config
from utils import validate_audio_file, format_error_message
from audio_processor import AudioProcessor
from llm_processor import LLMProcessor
from notion_integration import NotionClient


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


def save_transcript_on_error(transcript_text: str, original_filename: str) -> str:
    """Save transcript to file when LLM processing fails.

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

        progress_bar.progress(1.0)
        status_text.success("✅ Meeting minutes generated successfully!")
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

    if st.session_state.meeting_minutes:
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
    """Process uploaded audio file with Whisper + VAD."""
    upload_path = Config.UPLOAD_DIR / uploaded_file.name
    with open(upload_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    is_valid, error_msg = validate_audio_file(upload_path)
    if not is_valid:
        st.error(f"❌ {error_msg}")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(message: str, progress: float):
        status_text.info(f"⏳ {message}")
        progress_bar.progress(progress)

    # Step 1: Transcribe audio with Whisper + VAD
    update_progress("Initializing audio processor...", 0.1)
    audio_processor = AudioProcessor(
        progress_callback=lambda msg: update_progress(msg, 0.2)
    )

    update_progress("Transcribing audio with Whisper + VAD...", 0.3)
    print(f"[DEBUG] === 오디오 처리 시작 ===")
    print(f"[DEBUG] 파일 경로: {upload_path}")
    transcript_result = audio_processor.transcribe(upload_path)
    print(f"[DEBUG] === 오디오 처리 완료 ===")
    print(f"[DEBUG] 텍스트 길이: {len(transcript_result.get('text', ''))} 문자")
    print(f"[DEBUG] 세그먼트 수: {len(transcript_result.get('segments', []))}개")
    st.session_state.transcript_result = transcript_result

    audio_processor.cleanup()

    if not transcript_result.get('text'):
        st.warning("⚠️ No speech detected in the audio file")
        return

    # Step 2: Generate structured minutes with Gemini Pro
    update_progress("Generating meeting minutes with Gemini Pro...", 0.6)
    llm_processor = LLMProcessor()

    try:
        minutes = llm_processor.create_meeting_minutes(
            transcript=transcript_result['text'],
            manual_notes=manual_notes if manual_notes.strip() else None
        )

        st.session_state.meeting_minutes = minutes

        update_progress("Complete! 🎉", 1.0)
        status_text.success("✅ Meeting minutes generated successfully!")
        progress_bar.empty()

        upload_path.unlink(missing_ok=True)

        st.rerun()

    except Exception as llm_error:
        # LLM failed but transcript exists - save it to file
        progress_bar.empty()
        saved_path = save_transcript_on_error(
            transcript_result['text'],
            uploaded_file.name
        )
        upload_path.unlink(missing_ok=True)

        st.warning(f"⚠️ LLM 처리 실패, transcript가 저장되었습니다")
        st.info(f"📁 저장 위치: `{saved_path}`")
        st.error(format_error_message(llm_error))
        st.error("**Details:**")
        st.code(traceback.format_exc())


def display_results():
    """Display the generated meeting minutes with editing capability."""
    st.markdown("---")
    st.markdown('<div class="section-header">📄 Generated Meeting Minutes</div>', unsafe_allow_html=True)

    minutes = st.session_state.meeting_minutes
    # Use processing_id to create unique widget keys for each processing session
    pid = st.session_state.processing_id or 'default'

    st.markdown("**Edit the sections below before sending to Notion:**")

    st.markdown("### 📝 Summary")
    edited_summary = st.text_area(
        "Summary",
        value=minutes.get('summary', ''),
        height=100,
        key=f'edit_summary_{pid}',
        label_visibility='collapsed'
    )

    st.markdown("### 🔑 Key Updates")
    edited_key_updates = st.text_area(
        "Key Updates",
        value=minutes.get('key_updates', ''),
        height=150,
        key=f'edit_key_updates_{pid}',
        label_visibility='collapsed'
    )

    st.markdown("### 💬 Discussion Log")
    edited_discussion = st.text_area(
        "Discussion Log",
        value=minutes.get('discussion_log', ''),
        height=200,
        key=f'edit_discussion_{pid}',
        label_visibility='collapsed'
    )

    st.markdown("### ✅ Action Items")
    edited_action_items = st.text_area(
        "Action Items",
        value=minutes.get('action_items', ''),
        height=150,
        key=f'edit_action_items_{pid}',
        label_visibility='collapsed'
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📤 Send to Notion", type="primary", use_container_width=True):
            send_to_notion(
                edited_summary,
                edited_key_updates,
                edited_discussion,
                edited_action_items
            )

    if st.session_state.notion_url:
        st.success(f"✅ Successfully sent to Notion!")
        st.markdown(f"[🔗 Open in Notion]({st.session_state.notion_url})")


def send_to_notion(summary: str, key_updates: str, discussion: str, action_items: str):
    """Send the meeting minutes to Notion."""
    try:
        with st.spinner("Sending to Notion..."):
            notion_client = NotionClient()
            url = notion_client.create_meeting_minutes(
                summary=summary,
                key_updates=key_updates,
                discussion_log=discussion,
                action_items=action_items
            )
            st.session_state.notion_url = url
            st.rerun()
    except Exception as e:
        st.error(format_error_message(e))
        st.error("**Details:**")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
