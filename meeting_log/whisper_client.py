"""HTTP client for remote Whisper server."""

import requests
from pathlib import Path
from typing import Optional, Callable
from config import Config


class WhisperClient:
    """Calls Whisper HTTP server for audio transcription."""

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.server_url = Config.WHISPER_SERVER_URL
        self.model = Config.WHISPER_MODEL
        self.progress_callback = progress_callback

    def _update_progress(self, message: str):
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception:
                self.progress_callback = None

    def health_check(self) -> dict:
        """Check Whisper server status."""
        response = requests.get(f"{self.server_url}/health", timeout=10)
        response.raise_for_status()
        return response.json()

    def transcribe(self, audio_path: Path, language: str = "ko") -> dict:
        """Send audio file to Whisper server and return transcript.

        Returns dict with keys: text, segments, language, model_used
        (same interface as AudioProcessor.transcribe)
        """
        self._update_progress("Checking Whisper server...")
        health = self.health_check()
        self._update_progress(
            f"Server OK: {health.get('model_loaded', '?')} on {health.get('gpu_name', '?')}"
        )

        self._update_progress(f"Uploading {audio_path.name}...")
        with open(audio_path, "rb") as f:
            response = requests.post(
                f"{self.server_url}/transcribe",
                files={"file": (audio_path.name, f)},
                data={"model": self.model, "language": language},
                timeout=600,
            )
        response.raise_for_status()
        result = response.json()

        json_result = result.get("json_result", {})
        text = json_result.get("text", "")
        segments = json_result.get("segments", [])

        self._update_progress(f"Transcription complete ({len(text)} chars)")

        return {
            "text": text,
            "segments": segments,
            "language": json_result.get("language", "ko"),
            "model_used": result.get("model_used", "unknown"),
        }
