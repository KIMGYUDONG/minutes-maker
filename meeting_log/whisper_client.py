"""HTTP client for remote Whisper server."""

import time
import threading
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

    def _calc_timeout(self, audio_path: Path) -> int:
        """Estimate timeout from file size. ~1MB/min audio, processing ~1x realtime, 2x safety margin."""
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        estimated_minutes = max(size_mb / 1, 10)  # at least 10 minutes
        return int(estimated_minutes * 60 * 2)  # 2x safety margin

    def _poll_queue(self, stop_event: threading.Event):
        """Poll /queue every 30s to update progress and detect server hang."""
        while not stop_event.is_set():
            stop_event.wait(30)
            if stop_event.is_set():
                break
            try:
                resp = requests.get(f"{self.server_url}/queue", timeout=10)
                data = resp.json()
                active = data.get("active_job")
                if active and active.get("started_at"):
                    from datetime import datetime
                    started = datetime.fromisoformat(active["started_at"])
                    elapsed = datetime.now() - started
                    mins = int(elapsed.total_seconds() // 60)
                    secs = int(elapsed.total_seconds() % 60)
                    pending = data.get("queue_size", 0)
                    msg = f"Whisper 처리 중... ({mins}분 {secs}초 경과)"
                    if pending > 0:
                        msg += f" | 대기: {pending}"
                    self._update_progress(msg)
                elif active:
                    self._update_progress("Whisper 처리 중...")
                else:
                    self._update_progress("서버 응답 대기 중...")
            except Exception:
                self._update_progress("서버 상태 확인 실패, 계속 대기 중...")

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
        read_timeout = self._calc_timeout(audio_path)

        stop_polling = threading.Event()
        poll_thread = threading.Thread(
            target=self._poll_queue, args=(stop_polling,), daemon=True
        )
        poll_thread.start()

        try:
            with open(audio_path, "rb") as f:
                response = requests.post(
                    f"{self.server_url}/transcribe",
                    files={"file": (audio_path.name, f)},
                    data={"model": self.model, "language": language},
                    timeout=(30, read_timeout),
                )
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.ReadTimeout:
            self._update_progress("타임아웃 발생, 서버에서 결과 조회 중...")
            result = self._recover_result(audio_path.name)
            if not result:
                raise
        finally:
            stop_polling.set()
            poll_thread.join(timeout=5)

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

    def _recover_result(self, filename: str, max_wait: int = 300) -> Optional[dict]:
        """Poll /results to find saved result matching filename."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                resp = requests.get(f"{self.server_url}/results", timeout=10)
                for item in resp.json().get("results", []):
                    if item["filename"] == filename:
                        detail = requests.get(
                            f"{self.server_url}/results/{item['job_id']}", timeout=10
                        )
                        self._update_progress("서버에서 결과 복구 성공!")
                        return detail.json()
            except Exception:
                pass
            time.sleep(10)
        return None
