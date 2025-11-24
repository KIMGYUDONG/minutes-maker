"""Audio processing module using Whisper and silero-VAD."""

import warnings
warnings.filterwarnings("ignore")

import torch
import whisper
from pathlib import Path
from typing import Optional, Callable
import torchaudio
# soundfile backend ensures cross-platform compatibility (especially Windows)
try:
    torchaudio.set_audio_backend("soundfile")
except Exception:
    pass

from pydub import AudioSegment
from silero_vad import load_silero_vad, get_speech_timestamps
from datetime import datetime

from config import Config
from utils import format_timestamp


class AudioProcessor:
    """Handles audio transcription with Whisper and VAD."""
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize the audio processor.

        Args:
            progress_callback: Optional callback function for progress updates
        """
        self.progress_callback = progress_callback
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.vad_model = None
        self.current_model_name = None
        self.total_segments = 0  # For progress tracking

        # Long audio configuration (SPEC-005)
        self.LONG_AUDIO_THRESHOLD = 3600        # 1 hour in seconds
        self.SEGMENT_DURATION = 1800            # 30 minutes in seconds
        self.SEGMENT_OVERLAP = 30               # 30 seconds overlap

        self._update_progress("Initializing audio processor...")
    
    def _update_progress(self, message: str):
        """Update progress via callback if available."""
        if self.progress_callback:
            self.progress_callback(message)
    
    def _load_vad_model(self):
        """Load the silero-VAD model."""
        if self.vad_model is None:
            self._update_progress("Loading Voice Activity Detection model...")
            self.vad_model = load_silero_vad()
    
    def _load_whisper_model(self, model_name: str = None):
        """
        Load the Whisper model with CUDA optimization.
        
        Args:
            model_name: Model name to load (defaults to Config.WHISPER_MODEL)
        """
        if model_name is None:
            model_name = Config.WHISPER_MODEL

        if self.current_model_name == model_name and self.model is not None:
            return

        try:
            self._update_progress(f"Loading Whisper model ({model_name})...")

            if self.model is not None:
                del self.model
                torch.cuda.empty_cache()

            self.model = whisper.load_model(
                model_name,
                device=self.device
            )

            self.current_model_name = model_name
            self._update_progress(f"✅ Loaded {model_name} on {self.device}")
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                self._handle_oom_error(model_name)
            else:
                raise
    
    def _handle_oom_error(self, failed_model: str):
        """
        Handle CUDA Out of Memory error by falling back to smaller model.
        
        Args:
            failed_model: Name of the model that failed to load
        """
        self._update_progress(f"⚠️ GPU memory insufficient for {failed_model}")

        torch.cuda.empty_cache()

        fallback = Config.WHISPER_FALLBACK_MODEL
        if failed_model == fallback:
            # If fallback also fails, try medium
            fallback = "medium"
        
        self._update_progress(f"🔄 Retrying with {fallback}...")
        
        try:
            self.model = whisper.load_model(fallback, device=self.device)
            self.current_model_name = fallback
            self._update_progress(f"✅ Successfully loaded {fallback}")
        except Exception as e:
            raise RuntimeError(f"Failed to load fallback model: {str(e)}")
    
    def _convert_to_wav(self, audio_path: Path) -> Path:
        """
        Convert audio file to WAV format if needed.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Path to WAV file
        """
        if audio_path.suffix.lower() == ".wav":
            return audio_path

        self._update_progress(f"Converting {audio_path.suffix} to WAV...")

        audio = AudioSegment.from_file(str(audio_path))
        wav_path = audio_path.with_suffix(".wav")
        audio.export(str(wav_path), format="wav")
        
        return wav_path
    
    def _apply_vad(self, audio_path: Path) -> list:
        """
        Apply Voice Activity Detection to find speech segments.
        
        Args:
            audio_path: Path to WAV audio file
            
        Returns:
            List of speech timestamp dictionaries
        """
        self._load_vad_model()
        self._update_progress("Detecting speech segments with VAD...")

        wav, sample_rate = torchaudio.load(str(audio_path))

        if wav.shape[0] > 1:
            wav = torch.mean(wav, dim=0, keepdim=True)

        # silero-VAD requires 16kHz sample rate
        if sample_rate != Config.VAD_SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(sample_rate, Config.VAD_SAMPLE_RATE)
            wav = resampler(wav)
            sample_rate = Config.VAD_SAMPLE_RATE

        speech_timestamps = get_speech_timestamps(
            wav.squeeze(),
            self.vad_model,
            sampling_rate=sample_rate,
            threshold=Config.VAD_THRESHOLD,
            min_speech_duration_ms=Config.VAD_MIN_SPEECH_MS,
            min_silence_duration_ms=Config.VAD_MIN_SILENCE_MS,
        )
        
        total_speech_time = sum(
            (ts['end'] - ts['start']) / sample_rate
            for ts in speech_timestamps
        )
        
        self._update_progress(
            f"✅ Found {len(speech_timestamps)} speech segments "
            f"({total_speech_time:.1f}s of speech)"
        )
        
        return speech_timestamps
    
    def transcribe(self, audio_path: Path) -> dict:
        """
        Transcribe audio file with VAD-based preprocessing and long audio support.

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary with transcript and segments
        """
        try:
            wav_path = self._convert_to_wav(audio_path)

            # Check duration for long audio handling (SPEC-005)
            duration = self._get_audio_duration(wav_path)

            if self._is_long_audio(duration):
                # Long audio strategy: Segment and process
                self._update_progress(f"긴 오디오 감지 ({duration/60:.1f}분): 세그먼트로 처리합니다...")

                # Segment audio
                segments = self._segment_audio(wav_path)
                self.total_segments = len(segments)

                # Load Whisper model once
                self._load_whisper_model()

                # Transcribe each segment
                results = []
                for segment in segments:
                    result = self._transcribe_segment(segment)
                    results.append(result)

                # Merge transcripts
                self._update_progress("세그먼트 병합 중... (95%)")
                merged = self._merge_transcripts(results)

                # Cleanup temporary files
                self._cleanup_segments(segments)

                # Format results
                formatted_segments = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip(),
                        "timestamp": f"[{format_timestamp(seg['start'])}]"
                    }
                    for seg in merged.get("segments", [])
                ]

                self._update_progress("✅ 긴 오디오 전사 완료 (100%)")

                return {
                    "text": merged["text"],
                    "segments": formatted_segments,
                    "language": merged.get("language", "ko"),
                    "model_used": self.current_model_name,
                    "segments_processed": len(segments)
                }

            else:
                # Regular audio strategy: Process as single unit
                speech_timestamps = self._apply_vad(wav_path)

                if not speech_timestamps:
                    return {
                        "text": "",
                        "segments": [],
                        "warning": "No speech detected in audio file"
                    }

                # Load Whisper model
                self._load_whisper_model()

                # Transcribe with Whisper
                self._update_progress("Transcribing audio with Whisper...")

                try:
                    result = self.model.transcribe(
                        str(wav_path),
                        language="ko",  # Auto-detect, but prioritize Korean
                        task="transcribe",
                        fp16=False, # Fix: Force FP32 to avoid LayerNorm errors
                        verbose=False,
                    )

                    self._update_progress("✅ Transcription complete")

                    # Format results
                    return {
                        "text": result["text"].strip(),
                        "segments": [
                            {
                                "start": seg["start"],
                                "end": seg["end"],
                                "text": seg["text"].strip(),
                                "timestamp": f"[{format_timestamp(seg['start'])}]"
                            }
                            for seg in result["segments"]
                        ],
                        "language": result.get("language", "unknown"),
                        "model_used": self.current_model_name
                    }

                except RuntimeError as e:
                    if "out of memory" in str(e).lower():
                        torch.cuda.empty_cache()
                        self._handle_oom_error(self.current_model_name)
                        return self.transcribe(audio_path)
                    else:
                        raise

        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        Get audio duration in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        info = torchaudio.info(str(audio_path))
        return info.num_frames / info.sample_rate

    def _is_long_audio(self, duration_seconds: float) -> bool:
        """
        Check if audio requires segmentation (> 1 hour).

        Args:
            duration_seconds: Audio duration in seconds

        Returns:
            True if audio is longer than 1 hour
        """
        return duration_seconds > self.LONG_AUDIO_THRESHOLD

    def _segment_audio(self, audio_path: Path) -> list:
        """
        Segment long audio into 30-minute chunks with overlap.

        Args:
            audio_path: Path to audio file

        Returns:
            List of segment metadata dictionaries
        """
        self._update_progress("Segmenting long audio into 30-minute chunks...")

        # Load audio
        waveform, sample_rate = torchaudio.load(str(audio_path))

        # Calculate segment sizes in samples
        segment_samples = int(self.SEGMENT_DURATION * sample_rate)
        overlap_samples = int(self.SEGMENT_OVERLAP * sample_rate)

        total_samples = waveform.shape[1]
        segments = []
        start_sample = 0
        index = 0

        # Create segments
        while start_sample < total_samples:
            end_sample = min(start_sample + segment_samples, total_samples)

            # Extract segment with overlap
            segment_end = min(end_sample + overlap_samples, total_samples)
            segment_waveform = waveform[:, start_sample:segment_end]

            # Save temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                segment_path = Path(f.name)

            torchaudio.save(str(segment_path), segment_waveform, sample_rate)

            segments.append({
                "index": index,
                "start_time": start_sample / sample_rate,
                "end_time": end_sample / sample_rate,
                "path": segment_path,
                "duration": (segment_end - start_sample) / sample_rate
            })

            # Move to next segment (accounting for overlap)
            start_sample = end_sample
            index += 1

        self._update_progress(f"Created {len(segments)} segments")
        return segments

    def _transcribe_segment(self, segment: dict) -> dict:
        """
        Transcribe a single audio segment.

        Args:
            segment: Segment metadata dictionary

        Returns:
            Transcription result dictionary
        """
        try:
            # Update progress
            percent = int((segment["index"] + 1) * 75 / self.total_segments + 20)
            self._update_progress(
                f"분석 중: 세그먼트 {segment['index'] + 1}/{self.total_segments} ({percent}%)"
            )

            # Transcribe with Whisper
            result = self.model.transcribe(
                str(segment["path"]),
                language="ko",
                task="transcribe",
                fp16=False,
                verbose=False
            )

            # Clear GPU cache after each segment
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return {
                "index": segment["index"],
                "text": result["text"].strip(),
                "segments": result["segments"],
                "start_time": segment["start_time"]
            }

        except Exception as e:
            self._update_progress(f"⚠️ Segment {segment['index']} failed: {str(e)}")
            return {
                "index": segment["index"],
                "text": "",
                "segments": [],
                "error": str(e)
            }

    def _merge_transcripts(self, segment_results: list) -> dict:
        """
        Merge segment transcripts, removing overlap.

        Args:
            segment_results: List of segment transcription results

        Returns:
            Merged transcript dictionary
        """
        if not segment_results:
            return {"text": "", "segments": []}

        merged_text = ""
        merged_segments = []

        for i, result in enumerate(segment_results):
            if result.get("error"):
                continue

            if i == 0:
                # First segment: add everything
                merged_text = result["text"]
                merged_segments.extend(result["segments"])
            else:
                # Subsequent segments: trim overlap (simple text-based)
                # Skip segments in the overlap region (first 30 seconds)
                trimmed_segs = [
                    seg for seg in result["segments"]
                    if seg["start"] >= self.SEGMENT_OVERLAP
                ]

                # Adjust timestamps
                for seg in trimmed_segs:
                    seg["start"] += result["start_time"]
                    seg["end"] += result["start_time"]
                    merged_segments.append(seg)

                # Add text
                trimmed_text = " ".join(seg["text"] for seg in trimmed_segs)
                if trimmed_text:
                    merged_text += " " + trimmed_text

        return {
            "text": merged_text.strip(),
            "segments": merged_segments,
            "language": "ko"
        }

    def _cleanup_segments(self, segments: list):
        """
        Delete temporary segment files.

        Args:
            segments: List of segment metadata dictionaries
        """
        for segment in segments:
            try:
                if segment["path"].exists():
                    segment["path"].unlink()
            except Exception:
                pass  # Ignore cleanup errors

    def cleanup(self):
        """Clean up resources and free GPU memory."""
        if self.model is not None:
            del self.model
            self.model = None

        if self.vad_model is not None:
            del self.vad_model
            self.vad_model = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self._update_progress("Cleaned up audio processor resources")
