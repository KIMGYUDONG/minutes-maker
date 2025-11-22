# SPEC-002: Audio Processing

**Status**: Implemented
**Version**: 1.0
**Last Updated**: 2025-11-22
**Owner**: Meeting Minutes Team
**Dependencies**: SPEC-001 (Architecture)

---

## Overview

The Audio Processing module (`audio_processor.py`) handles the conversion of meeting audio recordings into text transcripts using OpenAI Whisper and silero-VAD for speech detection.

## Requirements

### Functional Requirements

**FR-001**: Support multiple audio formats (m4a, mp3, wav)
**FR-002**: Detect and filter speech segments using VAD
**FR-003**: Transcribe audio using OpenAI Whisper
**FR-004**: Handle GPU out-of-memory errors gracefully
**FR-005**: Provide progress callbacks for UI updates
**FR-006**: Clean up GPU resources after processing

### Non-Functional Requirements

**NFR-001**: Process audio in real-time or faster (with GPU)
**NFR-002**: Support files up to 100MB
**NFR-003**: Optimize GPU memory usage
**NFR-004**: Handle cross-platform audio backends (Windows/Mac/Linux)

## Architecture

### Class: AudioProcessor

```python
class AudioProcessor:
    """Handles audio transcription with Whisper and VAD."""

    def __init__(self, progress_callback: Optional[Callable] = None)
    def transcribe(self, audio_path: Path) -> dict
    def cleanup(self)

    # Private methods
    def _update_progress(self, message: str)
    def _load_vad_model(self)
    def _load_whisper_model(self, model_name: str = None)
    def _handle_oom_error(self, failed_model: str)
    def _convert_to_wav(self, audio_path: Path) -> Path
    def _apply_vad(self, audio_path: Path) -> list
```

### Component Diagram

```
AudioProcessor
├── Initialization
│   ├── Device Detection (CUDA/CPU)
│   ├── Progress Callback Setup
│   └── Model References (lazy-loaded)
│
├── Format Conversion
│   ├── Input: m4a/mp3/wav
│   ├── Process: pydub AudioSegment
│   └── Output: WAV file
│
├── VAD (Voice Activity Detection)
│   ├── Load: silero-VAD model
│   ├── Resample: 16kHz (if needed)
│   ├── Detect: Speech segments
│   └── Output: Timestamp list
│
├── Whisper Transcription
│   ├── Load: Whisper model (large-v3)
│   ├── Transcribe: Full audio file
│   ├── Fallback: large-v2 on OOM
│   └── Output: Text + segments
│
└── Cleanup
    ├── Delete: Whisper model
    ├── Delete: VAD model
    └── Clear: GPU cache
```

## Detailed Specifications

### 1. Initialization

**Purpose**: Set up the audio processor with device detection and callbacks

```python
def __init__(self, progress_callback: Optional[Callable] = None):
    """
    Initialize the audio processor.

    Args:
        progress_callback: Optional callback function for progress updates
    """
    self.progress_callback = progress_callback
    self.device = "cuda" if torch.cuda.is_available() else "cpu"
    self.model = None  # Lazy-loaded
    self.vad_model = None  # Lazy-loaded
    self.current_model_name = None

    self._update_progress("Initializing audio processor...")
```

**Behavior**:
- Detects CUDA availability
- Sets up lazy loading (models loaded on first use)
- Stores callback for UI progress updates

### 2. Audio Format Conversion

**Purpose**: Convert m4a/mp3 files to WAV format for processing

**Implementation**: `_convert_to_wav(audio_path: Path) -> Path`

**Process**:
1. Check if file is already WAV (skip conversion)
2. Load audio with pydub's AudioSegment
3. Export to WAV format
4. Return WAV file path

**Example**:
```python
# Input: meeting_audio.m4a
# Output: meeting_audio.wav (same directory)

audio = AudioSegment.from_file(str(audio_path))
wav_path = audio_path.with_suffix(".wav")
audio.export(str(wav_path), format="wav")
```

**Edge Cases**:
- Corrupted audio: pydub will raise exception
- Unsupported format: pydub error (caught by caller)
- Already WAV: Return original path (no conversion)

### 3. Voice Activity Detection (VAD)

**Purpose**: Detect speech segments to improve transcription accuracy

**Implementation**: `_apply_vad(audio_path: Path) -> list`

**Configuration** (from config.py):
```python
VAD_SAMPLE_RATE = 16000  # Required by silero-VAD
VAD_THRESHOLD = 0.5      # Speech detection threshold
VAD_MIN_SPEECH_MS = 250  # Minimum speech segment duration
VAD_MIN_SILENCE_MS = 500 # Minimum silence duration
```

**Process**:
1. Load audio with torchaudio
2. Convert to mono (if stereo)
3. Resample to 16kHz (if needed)
4. Apply silero-VAD model
5. Extract speech timestamps
6. Calculate total speech duration

**Output Format**:
```python
[
    {"start": 0, "end": 15360},      # Sample indices
    {"start": 18000, "end": 32400},
    ...
]
```

**Statistics**:
- Number of speech segments detected
- Total speech duration (seconds)
- Shown in progress callback

### 4. Whisper Transcription

**Purpose**: Convert speech to text using OpenAI Whisper

**Implementation**: `transcribe(audio_path: Path) -> dict`

**Model Configuration**:
- **Primary**: large-v3 (for RTX 3060 12GB)
- **Fallback**: large-v2 (on OOM)
- **Device**: CUDA (if available)
- **Precision**: FP32 (FP16 causes LayerNorm errors)

**Process**:
1. Convert audio to WAV
2. Apply VAD to detect speech
3. Load Whisper model (lazy-load with caching)
4. Transcribe with Whisper API
5. Handle OOM errors with fallback
6. Format and return results

**Whisper API Parameters**:
```python
result = self.model.transcribe(
    str(wav_path),
    language="ko",      # Prioritize Korean
    task="transcribe",  # Not translation
    fp16=False,         # FP32 to avoid LayerNorm errors
    verbose=False       # No console output
)
```

**Output Format**:
```python
{
    "text": "전체 회의 내용 텍스트",
    "segments": [
        {
            "start": 0.0,
            "end": 5.2,
            "text": "첫 번째 발화 내용",
            "timestamp": "[00:00]"
        },
        ...
    ],
    "language": "ko",
    "model_used": "large-v3"
}
```

**Special Cases**:
- **No speech detected**: Return empty text with warning
- **OOM error**: Retry with fallback model (recursive call)
- **Other errors**: Raise RuntimeError with details

### 5. GPU Memory Management

**Purpose**: Handle CUDA out-of-memory errors gracefully

**Implementation**: `_handle_oom_error(failed_model: str)`

**Fallback Chain**:
```
large-v3 (OOM) → large-v2 → medium (if large-v2 also fails)
```

**Process**:
1. Detect OOM error in exception message
2. Clear GPU cache: `torch.cuda.empty_cache()`
3. Load smaller fallback model
4. Update progress with warning
5. Retry transcription (recursive call in `transcribe()`)

**Error Messages**:
```
⚠️ GPU memory insufficient for large-v3
🔄 Retrying with large-v2...
✅ Successfully loaded large-v2
```

### 6. Model Loading

**Purpose**: Load Whisper and VAD models with caching

**Implementation**: `_load_whisper_model(model_name: str = None)`

**Behavior**:
- **First call**: Download and load model (~3GB for large-v3)
- **Subsequent calls**: Use cached model (if same name)
- **Model change**: Delete old model, load new one
- **GPU cache**: Clear on model change

**Lazy Loading Benefits**:
- Faster initialization
- Memory efficient (only load when needed)
- Allows multiple AudioProcessor instances without duplicate models

**VAD Model Loading**: `_load_vad_model()`
- Loads silero-VAD model (~5MB)
- Cached for reuse
- CPU-only (no GPU needed)

### 7. Resource Cleanup

**Purpose**: Free GPU memory and delete models

**Implementation**: `cleanup()`

**Process**:
```python
if self.model is not None:
    del self.model
    self.model = None

if self.vad_model is not None:
    del self.vad_model
    self.vad_model = None

if torch.cuda.is_available():
    torch.cuda.empty_cache()
```

**When to Call**:
- After successful transcription
- Before application exit
- When switching to different meeting

## Dependencies

### Python Packages
```
torch>=2.0.0          # PyTorch for deep learning
whisper               # OpenAI Whisper
torchaudio>=2.0.0     # Audio I/O
silero-vad>=5.0       # Voice Activity Detection
pydub>=0.25.1         # Audio format conversion
```

### External Dependencies
- **CUDA**: Optional but recommended (10x faster transcription)
- **ffmpeg**: Required by pydub for format conversion

### Hardware Requirements
- **Minimum**: 8GB RAM, CPU-only (slow transcription)
- **Recommended**: 12GB VRAM (NVIDIA GPU), RTX 3060 or better
- **Model Sizes**:
  - large-v3: ~3GB VRAM
  - large-v2: ~2.5GB VRAM
  - medium: ~1.5GB VRAM

## Error Handling

### Error Types

**1. File Errors**
```python
# Invalid audio file
raise RuntimeError("Transcription failed: [Errno 2] No such file or directory")
```

**2. Format Errors**
```python
# Unsupported audio format
raise RuntimeError("Transcription failed: Couldn't find ffmpeg or avconv")
```

**3. GPU Errors**
```python
# CUDA out of memory
RuntimeError: CUDA out of memory. Tried to allocate 3.00 GiB
→ Automatic fallback to smaller model
```

**4. Model Errors**
```python
# Whisper model not found
RuntimeError: Model 'invalid-model' not found
```

**5. VAD Errors**
```python
# Audio resampling error
RuntimeError: torchaudio backend not available
```

### Error Recovery Strategies

| Error Type | Recovery Strategy |
|------------|-------------------|
| OOM | Fallback to smaller model |
| Format Error | Attempt conversion with pydub |
| No Speech | Return empty result with warning |
| Model Error | Raise exception (user must fix) |
| GPU Error | Fall back to CPU |

## Testing Strategy

### Unit Tests (`tests/test_audio_processor.py`)
- Test model loading and caching
- Test OOM handling (mock)
- Test format conversion
- Test VAD detection
- Test result formatting

### Integration Tests (`tests/test_audio.py`)
- Test real audio file transcription
- Test GPU precision handling
- Test full pipeline (convert → VAD → transcribe)

### Test Files
- Sample audio: `tests/fixtures/sample_audio.m4a`
- Expected output: `tests/fixtures/expected_transcript.txt`

## Performance Metrics

### Benchmarks (RTX 3060 12GB)
| Model | Audio Length | Transcription Time | Speed |
|-------|--------------|-------------------|-------|
| large-v3 | 60 seconds | 30 seconds | 2x real-time |
| large-v2 | 60 seconds | 25 seconds | 2.4x real-time |
| medium | 60 seconds | 15 seconds | 4x real-time |

### VAD Benefits
- **Without VAD**: Process entire audio (including silence)
- **With VAD**: Process only speech segments (~30% time savings)

### Memory Usage
- **Whisper large-v3**: ~3GB VRAM
- **Whisper large-v2**: ~2.5GB VRAM
- **silero-VAD**: ~5MB RAM
- **Audio buffer**: ~50MB (per minute)

## Configuration

### Environment Variables
```bash
WHISPER_MODEL=large-v3
WHISPER_FALLBACK_MODEL=large-v2
```

### Config Constants (config.py)
```python
VAD_SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.5
VAD_MIN_SPEECH_MS = 250
VAD_MIN_SILENCE_MS = 500
```

## Future Enhancements

### Potential Improvements
1. **Speaker Diarization**: Identify and label different speakers
2. **Real-time Streaming**: Process audio as it's being recorded
3. **Custom VAD Threshold**: Let users adjust sensitivity
4. **Batch Processing**: Process multiple files at once
5. **Audio Quality Check**: Warn if audio quality is poor

### Technical Debt
- **Temporary Files**: WAV files not always cleaned up on error
- **Progress Granularity**: Progress jumps from 30% to 100% (no intermediate updates during Whisper)
- **Audio Backend**: soundfile backend may not work on all systems

---

**References**:
- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [silero-VAD Documentation](https://github.com/snakers4/silero-vad)
- [torchaudio Documentation](https://pytorch.org/audio/)
- [pydub Documentation](https://github.com/jiaaro/pydub)
