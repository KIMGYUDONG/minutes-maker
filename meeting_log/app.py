"""Streamlit UI for the meeting minutes service."""

import streamlit as st
from pathlib import Path
import traceback
from datetime import datetime

from config import Config
from utils import validate_audio_file, format_error_message, get_meeting_title
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
        
        import torch
        if torch.cuda.is_available():
            st.success(f"✅ GPU: {torch.cuda.get_device_name(0)}")
            st.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            st.warning("⚠️ GPU not available")
        
        st.markdown(f"**Model**: {Config.WHISPER_MODEL}")
        st.markdown(f"**Fallback**: {Config.WHISPER_FALLBACK_MODEL}")


def main():
    """Main application."""
    initialize_session_state()
    validate_configuration()
    Config.setup_directories()
    show_sidebar()
    
    # Main header
    st.markdown('<div class="main-header">📋 Automated Meeting Minutes</div>', unsafe_allow_html=True)
    st.markdown("Transform your meeting recordings into structured minutes with AI")
    
    # Create two columns for input
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="section-header">🎤 Audio Upload</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload your meeting recording",
            type=['m4a', 'mp3', 'wav'],
            help="Supported formats: m4a, mp3, wav (max 500MB)"
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
    
    # Process button
    st.markdown("---")
    
    if uploaded_file:
        if st.button("🚀 Generate Meeting Minutes", type="primary", use_container_width=True):
            process_meeting(uploaded_file, manual_notes)
    else:
        st.info("👆 Please upload an audio file to get started")
    
    # Display results
    if st.session_state.meeting_minutes:
        display_results()


def process_meeting(uploaded_file, manual_notes: str):
    """Process the meeting audio and generate minutes."""
    try:
        # Save uploaded file
        upload_path = Config.UPLOAD_DIR / uploaded_file.name
        with open(upload_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Validate audio file
        is_valid, error_msg = validate_audio_file(upload_path)
        if not is_valid:
            st.error(f"❌ {error_msg}")
            return
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(message: str, progress: float):
            status_text.info(f"⏳ {message}")
            progress_bar.progress(progress)
        
        # Step 1: Transcribe audio
        update_progress("Initializing audio processor...", 0.1)
        audio_processor = AudioProcessor(
            progress_callback=lambda msg: update_progress(msg, 0.2)
        )
        
        update_progress("Transcribing audio with Whisper + VAD...", 0.3)
        transcript_result = audio_processor.transcribe(upload_path)
        st.session_state.transcript_result = transcript_result
        
        audio_processor.cleanup()
        
        if not transcript_result.get('text'):
            st.warning("⚠️ No speech detected in the audio file")
            return
        
        # Step 2: Generate meeting minutes with LLM
        update_progress("Generating meeting minutes with Gemini Pro...", 0.6)
        llm_processor = LLMProcessor()
        minutes = llm_processor.create_meeting_minutes(
            transcript=transcript_result['text'],
            manual_notes=manual_notes if manual_notes.strip() else None
        )
        
        st.session_state.meeting_minutes = minutes
        
        update_progress("Complete! 🎉", 1.0)
        status_text.success("✅ Meeting minutes generated successfully!")
        progress_bar.empty()
        
        # Clean up uploaded file
        upload_path.unlink(missing_ok=True)
        
    except Exception as e:
        st.error(format_error_message(e))
        st.error("**Details:**")
        st.code(traceback.format_exc())


def display_results():
    """Display the generated meeting minutes with editing capability."""
    st.markdown("---")
    st.markdown('<div class="section-header">📄 Generated Meeting Minutes</div>', unsafe_allow_html=True)
    
    minutes = st.session_state.meeting_minutes
    
    # Editable sections
    st.markdown("**Edit the sections below before sending to Notion:**")
    
    # Summary
    st.markdown("### 📝 Summary")
    edited_summary = st.text_area(
        "Summary",
        value=minutes.get('summary', ''),
        height=100,
        key='edit_summary',
        label_visibility='collapsed'
    )
    
    # Key Updates
    st.markdown("### 🔑 Key Updates")
    edited_key_updates = st.text_area(
        "Key Updates",
        value=minutes.get('key_updates', ''),
        height=150,
        key='edit_key_updates',
        label_visibility='collapsed'
    )
    
    # Discussion Log
    st.markdown("### 💬 Discussion Log")
    edited_discussion = st.text_area(
        "Discussion Log",
        value=minutes.get('discussion_log', ''),
        height=200,
        key='edit_discussion',
        label_visibility='collapsed'
    )
    
    # Action Items
    st.markdown("### ✅ Action Items")
    edited_action_items = st.text_area(
        "Action Items",
        value=minutes.get('action_items', ''),
        height=150,
        key='edit_action_items',
        label_visibility='collapsed'
    )
    
    # Send to Notion button
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
    
    # Show Notion link if sent
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
