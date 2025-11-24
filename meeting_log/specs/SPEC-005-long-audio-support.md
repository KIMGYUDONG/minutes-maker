# SPEC-005: Long Audio Support

**Status**: Proposed
**Version**: 1.0
**Last Updated**: 2025-11-24
**Owner**: Meeting Minutes Team
**Dependencies**: SPEC-001 (Architecture), SPEC-002 (Audio Processing), SPEC-003 (LLM Integration)

---

## Overview

The Meeting Minutes Generator currently processes audio files but encounters errors with very long recordings (2+ hours). This specification extends the audio processing pipeline to support extended recordings through intelligent segmentation, enabling reliable transcription of meetings up to 8 hours.

**Key Problem**: 1시간 20분 음성 메모 처리 시 Gemini API multi-part response 오류 발생

**Solution**: 긴 오디오를 30분 세그먼트로 분할 → 개별 전사 → 병합

---

## Requirements

### Functional Requirements

**FR-001**: Support audio files up to 8 hours (28,800 seconds)
**FR-002**: Implement automatic audio segmentation for files longer than 1 hour
**FR-003**: Preserve speaker context and continuity across segments
**FR-004**: Handle segment boundary artifacts intelligently
**FR-005**: Merge segment transcripts with proper timing
**FR-006**: Provide progress tracking during long transcription
**FR-007**: Gracefully handle partial failures (one segment fails)

### Non-Functional Requirements

**NFR-001**: Transcribe 8-hour audio within 4 hours (2x real-time with GPU)
**NFR-002**: Use <4GB VRAM consistently (prevent GPU OOM)
**NFR-003**: Support files up to 500MB
**NFR-004**: Maintain 37 existing behavior tests passing
**NFR-005**: Add 10-15 new behavior tests for segmentation

---

## Architecture

### Extended AudioProcessor Class

```python
class AudioProcessor:
    """Enhanced audio processor with long audio support."""

    # Existing methods
    def __init__(self, progress_callback: Optional[Callable] = None)
    def transcribe(self, audio_path: Path) -> dict
    def cleanup(self)

    # New methods for long audio
    def _is_long_audio(self, duration_seconds: float) -> bool
    def _segment_audio(self, audio_path: Path) -> List[Dict]
    def _transcribe_segment(self, segment: Dict) -> dict
    def _merge_transcripts(self, segments: List[dict]) -> dict
    def _cleanup_segments(self, segments: List[Dict])
    def _cleanup_gpu_cache(self)
```

### Processing Flow

```
                    ┌─────────────────┐
                    │  Audio Input    │
                    │  (1-8 hours)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Get Duration    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Duration > 1hr? │
                    └────┬────────┬───┘
                         │        │
                     Yes │        │ No
                         │        │
            ┌────────────▼──┐     │
            │ Segmentation  │     │
            │ (30min chunks)│     │
            └───────┬───────┘     │
                    │             │
        ┌───────────▼─────────┐   │
        │ For each segment:   │   │
        │ 1. Transcribe       │   │
        │ 2. Clear GPU        │   │
        │ 3. Update progress  │   │
        └───────┬─────────────┘   │
                │                 │
        ┌───────▼─────────┐       │
        │ Merge Transcripts│      │
        │ (remove overlap) │      │
        └───────┬─────────┘       │
                │                 │
                └─────────┬───────┘
                          │
                  ┌───────▼───────┐
                  │ Final Output  │
                  └───────────────┘
```

---

## Detailed Specifications

### 1. Duration Detection

**Threshold**: 1 hour (3600 seconds)

```python
def _is_long_audio(self, duration_seconds: float) -> bool:
    """Returns True if audio duration > 1 hour."""
    return duration_seconds > 3600
```

**Why 1 hour?**
- Whisper large-v3 handles up to 30 minutes reliably
- GPU memory risk increases significantly after 1 hour
- Allows graceful degradation strategy

---

### 2. Audio Segmentation

**Configuration**:
```python
SEGMENT_DURATION_SECONDS = 1800      # 30 minutes
SEGMENT_OVERLAP_SECONDS = 30         # 30-second overlap
```

**Implementation**:
```python
def _segment_audio(self, audio_path: Path) -> List[Dict]:
    """Split long audio into 30-minute chunks with 30-second overlap."""

    # 1. Load audio with torchaudio
    waveform, sample_rate = torchaudio.load(audio_path)

    # 2. Calculate segments
    segment_samples = SEGMENT_DURATION_SECONDS * sample_rate
    overlap_samples = SEGMENT_OVERLAP_SECONDS * sample_rate

    segments = []
    start_sample = 0
    index = 0

    # 3. Create segments
    while start_sample < waveform.shape[1]:
        end_sample = min(start_sample + segment_samples, waveform.shape[1])

        # Extract segment with overlap
        segment_waveform = waveform[:, start_sample:end_sample + overlap_samples]

        # Save temporary file
        segment_path = Path(f"/tmp/segment_{index}.wav")
        torchaudio.save(segment_path, segment_waveform, sample_rate)

        segments.append({
            "index": index,
            "start_time": start_sample / sample_rate,
            "end_time": end_sample / sample_rate,
            "path": segment_path
        })

        # Move to next segment (accounting for overlap)
        start_sample = end_sample - overlap_samples
        index += 1

    return segments
```

**Overlap Strategy**:
```
Audio: |----30min----|----30min----|----30min----|
Seg 0: |----30min----| overlap 30s
Seg 1:              overlap 30s|----30min----|overlap 30s
Seg 2:                                      overlap 30s|----30min----|
```

---

### 3. Segment Transcription

```python
def _transcribe_segment(self, segment: Dict) -> dict:
    """Transcribe single segment with progress tracking."""

    try:
        # Update progress
        if self.progress_callback:
            percent = (segment["index"] + 1) * 75 // self.total_segments + 20
            self.progress_callback(
                f"분석 중: 세그먼트 {segment['index'] + 1}/{self.total_segments} ({percent}%)"
            )

        # Transcribe with Whisper
        result = self.model.transcribe(
            str(segment["path"]),
            language="ko",
            verbose=False
        )

        # Clear GPU cache
        self._cleanup_gpu_cache()

        return {
            "index": segment["index"],
            "text": result["text"],
            "segments": result["segments"],
            "start_time": segment["start_time"]
        }

    except Exception as e:
        # Log error but continue
        print(f"⚠️ Segment {segment['index']} failed: {str(e)}")
        return {
            "index": segment["index"],
            "text": "",
            "segments": [],
            "error": str(e)
        }
```

---

### 4. Transcript Merging

**Challenge**: Remove overlapping text at boundaries

```python
def _merge_transcripts(self, segments: List[dict]) -> dict:
    """Merge segment transcripts, removing overlap."""

    if not segments:
        return {"text": "", "segments": []}

    merged_text = ""
    merged_segments = []

    for i, segment in enumerate(segments):
        if segment.get("error"):
            continue

        if i == 0:
            # First segment: add everything
            merged_text = segment["text"]
            merged_segments.extend(segment["segments"])
        else:
            # Subsequent segments: remove overlap
            # Simple approach: trim first 30 seconds of text
            segment_text = self._trim_overlap(segment["text"], segment["segments"])
            merged_text += " " + segment_text

            # Adjust timestamps
            for seg in segment["segments"]:
                if seg["start"] >= SEGMENT_OVERLAP_SECONDS:
                    seg["start"] += segment["start_time"]
                    seg["end"] += segment["start_time"]
                    merged_segments.append(seg)

    return {
        "text": merged_text,
        "segments": merged_segments,
        "language": "ko"
    }

def _trim_overlap(self, text: str, segments: list) -> str:
    """Remove first 30 seconds of text (overlap region)."""
    # Find segments after overlap
    trimmed_segments = [s for s in segments if s["start"] >= SEGMENT_OVERLAP_SECONDS]
    return " ".join(s["text"] for s in trimmed_segments)
```

---

### 5. Memory Management

```python
def _cleanup_segments(self, segments: List[Dict]):
    """Delete temporary segment files."""
    for segment in segments:
        if segment["path"].exists():
            segment["path"].unlink()

def _cleanup_gpu_cache(self):
    """Clear GPU memory between segments."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

**Memory Strategy**:
- Process ONE segment at a time
- Clear GPU after each segment
- Reuse Whisper model (load once)
- Delete temp files immediately after transcription

---

### 6. Updated transcribe() Method

```python
def transcribe(self, audio_path: Path) -> dict:
    """Transcribe audio with automatic long-audio handling."""

    # Get duration
    duration = self._get_duration(audio_path)

    # Check if long audio
    if self._is_long_audio(duration):
        # Segmentation strategy
        if self.progress_callback:
            self.progress_callback("긴 오디오 감지: 세그먼트로 처리합니다...")

        # Segment audio
        segments = self._segment_audio(audio_path)
        self.total_segments = len(segments)

        # Transcribe each segment
        results = []
        for segment in segments:
            result = self._transcribe_segment(segment)
            results.append(result)

        # Merge transcripts
        if self.progress_callback:
            self.progress_callback("세그먼트 병합 중... (95%)")

        merged = self._merge_transcripts(results)

        # Cleanup
        self._cleanup_segments(segments)

        if self.progress_callback:
            self.progress_callback("완료! (100%)")

        return merged
    else:
        # Regular transcription (existing logic)
        if self.progress_callback:
            self.progress_callback("오디오 분석 중...")

        result = self.model.transcribe(
            str(audio_path),
            language="ko",
            verbose=False
        )

        if self.progress_callback:
            self.progress_callback("완료! (100%)")

        return result
```

---

## Error Handling

### Error Types

| Error | Cause | Recovery |
|-------|-------|----------|
| **GPU OOM** | Segment too large | Use smaller model (medium) |
| **Segment transcription fails** | Model error | Log warning, continue with empty |
| **File I/O error** | Corrupted audio | Fail fast with clear message |
| **Merge error** | Overlap mismatch | Simple concatenation fallback |

### Example: OOM Recovery

```python
try:
    result = self.model.transcribe(...)
except RuntimeError as e:
    if "CUDA out of memory" in str(e):
        print("⚠️ GPU OOM - falling back to smaller model")
        self._load_smaller_model()  # medium or small
        result = self.model.transcribe(...)
    else:
        raise
```

---

## Testing Strategy

### Behavior Tests

**File**: `tests/behavior/test_audio_long_behavior.py`

```python
class TestLongAudioDetection:
    """Behavior: Detects when audio requires segmentation."""

    def test_audio_under_1_hour_uses_regular_pipeline()
    def test_audio_over_1_hour_uses_segmentation()
    def test_exactly_1_hour_boundary_condition()

class TestAudioSegmentation:
    """Behavior: Segments long audio correctly."""

    def test_2_hour_audio_segments_into_4_chunks()
    def test_segments_have_30_second_overlap()
    def test_segment_files_are_valid_wav()
    def test_last_segment_handles_remainder()

class TestSegmentTranscription:
    """Behavior: Transcribes segments independently."""

    def test_transcribes_each_segment_with_whisper()
    def test_updates_progress_during_processing()
    def test_recovers_from_single_segment_failure()

class TestTranscriptMerging:
    """Behavior: Merges segments without duplication."""

    def test_merges_two_segments_correctly()
    def test_removes_30_second_overlap()
    def test_adjusts_timestamps_for_merged_result()

class TestMemoryManagement:
    """Behavior: Manages GPU memory efficiently."""

    def test_cleans_up_temporary_files()
    def test_clears_gpu_cache_between_segments()
    def test_maintains_3gb_vram_usage()
```

**Test Count**: 10-15 new behavior tests

**Coverage Goal**: 70%+ (maintain existing standard)

---

## Performance Metrics

### Expected Performance (RTX 3060 12GB)

| Duration | Segments | Processing Time | Speed | VRAM |
|----------|----------|----------------|-------|------|
| 30 min | 1 (no segmentation) | 15 min | 2x | 3GB |
| 1 hour | 1 (no segmentation) | 30 min | 2x | 3GB |
| 2 hours | 4 | 60 min | 2x | 3GB |
| 4 hours | 8 | 120 min | 2x | 3GB |
| 8 hours | 16 | 240 min | 2x | 3GB |

**Key Metric**: VRAM usage remains constant at 3GB regardless of audio length

---

## Dependencies

### Python Packages
```
torch>=2.0.0          # GPU processing
torchaudio>=2.0.0     # Audio segmentation
whisper               # Transcription (unchanged)
```

### Configuration
```python
# audio_processor.py
LONG_AUDIO_THRESHOLD = 3600        # 1 hour in seconds
SEGMENT_DURATION_SECONDS = 1800    # 30 minutes
SEGMENT_OVERLAP_SECONDS = 30       # 30 seconds
```

---

## Limitations

### Current Limitations
1. **No speaker diarization**: Cannot identify individual speakers across segments
2. **Simple overlap handling**: Text-based trimming may not be perfect
3. **Sequential processing**: Segments processed one at a time (no parallelization)
4. **Fixed segment size**: Always 30 minutes (no dynamic adjustment)

### Workarounds
- **Speaker ID**: Add manually in Notion after generation
- **Overlap issues**: Review final transcript for boundary artifacts
- **Processing time**: GPU acceleration keeps it manageable (2x real-time)

---

## Future Enhancements

1. **Parallel Segment Processing**: Process multiple segments on multi-GPU systems
2. **Dynamic Segmentation**: Adjust based on silence detection
3. **Speaker Diarization**: Identify speakers across boundaries
4. **Streaming Support**: Process audio as it's being recorded
5. **Adaptive Quality**: Choose model based on available VRAM

---

## Implementation Checklist

- [ ] Add `_is_long_audio()` method
- [ ] Implement `_segment_audio()` with torchaudio
- [ ] Implement `_transcribe_segment()` with progress
- [ ] Implement `_merge_transcripts()` with overlap removal
- [ ] Add GPU cleanup methods
- [ ] Update `transcribe()` to handle long audio
- [ ] Add 10-15 behavior tests
- [ ] Verify all 37 existing tests still pass
- [ ] Test with 2-hour real audio
- [ ] Document in README.md

---

## References

- [OpenAI Whisper - Long Audio Discussion](https://github.com/openai/whisper/discussions/557)
- [torchaudio Documentation](https://pytorch.org/audio/)
- SPEC-002: Audio Processing
- SPEC-003: LLM Integration
