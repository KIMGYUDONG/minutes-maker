"""Utility functions for the meeting minutes service."""

from pathlib import Path
from datetime import datetime
from typing import Optional
from config import Config


def validate_audio_file(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate an audio file.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if file exists
    if not file_path.exists():
        return False, "File does not exist"
    
    # Check file extension
    if file_path.suffix.lower() not in Config.SUPPORTED_FORMATS:
        return False, f"Unsupported format. Supported formats: {', '.join(Config.SUPPORTED_FORMATS)}"
    
    # Check file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > Config.MAX_FILE_SIZE_MB:
        return False, f"File size ({file_size_mb:.1f}MB) exceeds maximum ({Config.MAX_FILE_SIZE_MB}MB)"
    
    return True, None


def format_timestamp(seconds: float) -> str:
    """
    Format seconds into HH:MM:SS timestamp.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def get_meeting_title() -> str:
    """
    Generate a meeting title with current date and time.
    
    Returns:
        Meeting title string
    """
    now = datetime.now()
    return now.strftime("Meeting Minutes - %Y-%m-%d %H:%M")


def format_error_message(error: Exception) -> str:
    """
    Format an error message for display.
    
    Args:
        error: The exception object
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    return f"❌ {error_type}: {str(error)}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def chunk_text(text: str, limit: int = 2000) -> list[str]:
    """
    Split text into chunks of a maximum size.
    
    Args:
        text: Text to split
        limit: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= limit:
        return [text]
        
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
            
        # Find a good split point (space) within the limit
        split_idx = text.rfind(' ', 0, limit)
        if split_idx == -1:
            # No space found, force split at limit
            split_idx = limit
            
        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip()
        
    return chunks
