"""Configuration management for the meeting minutes service."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""

    # Demo Mode (for Streamlit Cloud deployment)
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")
    GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "8192"))
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
    NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "")
    
    # Whisper Configuration
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
    WHISPER_FALLBACK_MODEL = os.getenv("WHISPER_FALLBACK_MODEL", "large-v2")
    
    # Server Configuration
    STREAMLIT_SERVER_ADDRESS = os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    STREAMLIT_SERVER_PORT = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
    
    # Audio Configuration
    SUPPORTED_FORMATS = [".m4a", ".mp3", ".wav"]
    MAX_FILE_SIZE_MB = 500  # Maximum audio file size

    # Text Configuration (for transcript upload)
    TEXT_FORMATS = [".txt"]
    ALL_UPLOAD_FORMATS = SUPPORTED_FORMATS + TEXT_FORMATS

    # VAD (Voice Activity Detection) Configuration
    VAD_SAMPLE_RATE = 16000  # Required sample rate for VAD
    VAD_THRESHOLD = 0.5  # Speech probability threshold
    VAD_MIN_SPEECH_MS = 250  # Minimum speech duration in milliseconds
    VAD_MIN_SILENCE_MS = 500  # Minimum silence duration to split on
    
    # Paths
    BASE_DIR = Path(__file__).parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")
        
        if not cls.NOTION_TOKEN:
            errors.append("NOTION_TOKEN is not set")
        
        if not cls.NOTION_PAGE_ID:
            errors.append("NOTION_PAGE_ID is not set")
        
        return errors
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
