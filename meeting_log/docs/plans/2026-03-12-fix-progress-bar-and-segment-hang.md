# Fix: Progress Bar Disappearing & Short Segment Hang

**Date**: 2026-03-12
**Status**: Revised (Critic review v1 applied)
**Issues**: 3 related problems in long audio processing pipeline

---

## Problem Summary

| # | Issue | Severity | Root Cause |
|---|-------|----------|------------|
| 1 | Progress bar disappears during 15+ min processing | High | `app.py:359` blocks main thread → WebSocket timeout → Streamlit rerun |
| 2 | Short final segment (<60s) causes intermittent GPU hang | High | `audio_processor.py:388-411` creates 28s segment → Whisper deadlocks on fragmented GPU memory |
| 3 | Overlap trimming deletes short segment text | Medium | `audio_processor.py:502-504` filters out all segments where `start < 30s` |

---

## Task Flow Diagram

```
Phase 1: Short Segment Fix          Phase 2: Transcribe Timeout
(audio_processor.py)                (audio_processor.py)
├─ 1a. Add MIN_SEGMENT_DURATION     ├─ 2a. Add ThreadPoolExecutor timeout
├─ 1b. Merge short final segment    └─ 2b. Handle timeout fallback
├─ 1c. Fix overlap trimming bug
└─ 1d. Tests
        │                                    │
        ▼                                    ▼
        ╰────────────┬───────────────────────╯
                     ▼
           Phase 3: Background Thread
           (app.py)
           ├─ 3a. Module-level worker registry
           ├─ 3b. Background thread pipeline
           ├─ 3c. Status-driven polling UI
           ├─ 3d. Streamlit config
           └─ 3e. Tests
                     │
                     ▼
              Phase 4: Verification
              ├─ 4a. All tests pass
              └─ 4b. Manual E2E on Windows

Phase 1, 2: parallel (independent)
Phase 3: depends on Phase 1, 2
Phase 4: depends on Phase 3
```

---

## Phase 1: Short Final Segment Fix (audio_processor.py)

### TODO 1a: Add MIN_SEGMENT_DURATION constant

**File**: `audio_processor.py:43-46`

**Before**:
```python
self.LONG_AUDIO_THRESHOLD = 3600        # 1 hour in seconds
self.SEGMENT_DURATION = 1800            # 30 minutes in seconds
self.SEGMENT_OVERLAP = 30               # 30 seconds overlap
```

**After**:
```python
self.LONG_AUDIO_THRESHOLD = 3600        # 1 hour in seconds
self.SEGMENT_DURATION = 1800            # 30 minutes in seconds
self.SEGMENT_OVERLAP = 30               # 30 seconds overlap
self.MIN_SEGMENT_DURATION = 60          # minimum segment length in seconds
```

### TODO 1b: Merge short final segment into previous

**File**: `audio_processor.py:363-415` (`_segment_audio` method)

**Before** (after while loop, ~line 411):
```python
        # Move to next segment (accounting for overlap)
        start_sample = end_sample
        index += 1

    self._update_progress(f"Created {len(segments)} segments")
    return segments
```

**After**:
```python
        # Move to next segment (accounting for overlap)
        start_sample = end_sample
        index += 1

    # Merge short final segment into previous to prevent GPU hang
    # NOTE: waveform, sample_rate, total_samples are from lines 376, 382 (still in scope)
    if len(segments) > 1:
        last = segments[-1]
        if last["duration"] < self.MIN_SEGMENT_DURATION:
            prev = segments[-2]
            # Extend previous segment to end of audio
            extended_end = total_samples
            start_pos = int(prev["start_time"] * sample_rate)
            extended_waveform = waveform[:, start_pos:extended_end]

            # Overwrite previous segment file
            torchaudio.save(str(prev["path"]), extended_waveform, sample_rate)
            prev["end_time"] = last["end_time"]
            prev["duration"] = (extended_end - start_pos) / sample_rate

            # Remove short segment and its temp file
            last["path"].unlink(missing_ok=True)
            segments.pop()

    self._update_progress(f"Created {len(segments)} segments")
    return segments
```

**Verification**: 60.5분 오디오 → 2개 세그먼트 (30분+30.5분), 세그먼트 3 제거됨

### TODO 1c: Fix overlap trimming for short segments (defensive)

**File**: `audio_processor.py:499-504` (`_merge_transcripts` method)

**Before**:
```python
        else:
            # Subsequent segments: trim overlap (simple text-based)
            # Skip segments in the overlap region (first 30 seconds)
            trimmed_segs = [
                seg for seg in result["segments"]
                if seg["start"] >= self.SEGMENT_OVERLAP
            ]
```

**After**:
```python
        else:
            # Subsequent segments: trim overlap (simple text-based)
            segment_duration = result.get("duration", float('inf'))
            if segment_duration <= self.SEGMENT_OVERLAP:
                # Segment shorter than overlap: keep all (no trimming)
                trimmed_segs = result["segments"]
            else:
                # Skip segments in the overlap region (first 30 seconds)
                trimmed_segs = [
                    seg for seg in result["segments"]
                    if seg["start"] >= self.SEGMENT_OVERLAP
                ]
```

**Note**: `_transcribe_segment` return dict에 `duration` 필드 추가 필요:

**File**: `audio_processor.py:456-462`

**Before**:
```python
        return {
            "index": segment["index"],
            "text": result["text"].strip(),
            "segments": result["segments"],
            "start_time": segment["start_time"]
        }
```

**After**:
```python
        return {
            "index": segment["index"],
            "text": result["text"].strip(),
            "segments": result["segments"],
            "start_time": segment["start_time"],
            "duration": segment.get("duration", 0)
        }
```

### TODO 1d: Tests

**File**: `tests/behavior/test_audio_long_behavior.py` (기존 파일에 추가)

**Test fixture strategy**: `torchaudio.save()`로 synthetic silence WAV를 생성합니다.
실제 Whisper 호출은 하지 않고 `_segment_audio`와 `_merge_transcripts` 메서드만 단위 테스트합니다.

```python
import torch
import torchaudio
import tempfile

def _create_silent_wav(duration_seconds: float, sample_rate: int = 16000) -> Path:
    """Create a silent WAV file for testing segmentation logic."""
    samples = int(duration_seconds * sample_rate)
    waveform = torch.zeros(1, samples)
    path = Path(tempfile.mktemp(suffix=".wav"))
    torchaudio.save(str(path), waveform, sample_rate)
    return path


class TestShortFinalSegment:
    """Short final segments should be merged into previous segment."""

    @pytest.mark.skipif(not HAS_TORCH, reason="No torch")
    def test_short_final_segment_merged_into_previous(self):
        """When last segment < MIN_SEGMENT_DURATION, merge into previous."""
        processor = AudioProcessor()
        # 60.5 min = 3630s → would create 3 segments (1800, 1800, 30)
        # After merge: 2 segments (1800, 1830)
        wav_path = _create_silent_wav(3630)
        try:
            segments = processor._segment_audio(wav_path)
            assert len(segments) == 2
            assert segments[-1]["duration"] > processor.MIN_SEGMENT_DURATION
        finally:
            wav_path.unlink(missing_ok=True)
            for seg in segments:
                seg["path"].unlink(missing_ok=True)

    @pytest.mark.skipif(not HAS_TORCH, reason="No torch")
    def test_segment_at_boundary_not_merged(self):
        """When last segment >= MIN_SEGMENT_DURATION, keep it separate."""
        processor = AudioProcessor()
        # 62 min = 3720s → 3 segments (1800, 1800, 120)
        # 120s > 60s MIN → keep 3 segments
        wav_path = _create_silent_wav(3720)
        try:
            segments = processor._segment_audio(wav_path)
            assert len(segments) == 3
        finally:
            wav_path.unlink(missing_ok=True)
            for seg in segments:
                seg["path"].unlink(missing_ok=True)

    def test_overlap_trimming_handles_short_segment(self):
        """_merge_transcripts doesn't discard text from short segments."""
        processor = AudioProcessor()
        segment_results = [
            {"index": 0, "text": "first", "segments": [
                {"start": 0, "end": 10, "text": "first"}
            ], "start_time": 0, "duration": 1800},
            {"index": 1, "text": "second", "segments": [
                {"start": 5, "end": 20, "text": "second"}
            ], "start_time": 1800, "duration": 25},  # < SEGMENT_OVERLAP (30s)
        ]
        merged = processor._merge_transcripts(segment_results)
        assert "second" in merged["text"]  # Must NOT be trimmed
```

---

## Phase 2: Transcribe Timeout Safety Net (audio_processor.py)

### TODO 2a: Add timeout to model.transcribe()

**File**: `audio_processor.py:439-445` (`_transcribe_segment` method)

**Before**:
```python
        # Transcribe with Whisper
        result = self.model.transcribe(
            str(segment["path"]),
            language="ko",
            task="transcribe",
            fp16=False,
            verbose=False
        )
```

**After**:
```python
        # Transcribe with Whisper (timeout safety net)
        # CRITICAL: Do NOT use `with ThreadPoolExecutor(...)` context manager.
        # The `with` block calls shutdown(wait=True) on exit, which blocks
        # forever if the Whisper thread is still running after timeout.
        timeout_seconds = max(int(segment.get("duration", 1800) * 0.5), 300)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.model.transcribe,
            str(segment["path"]),
            language="ko",
            task="transcribe",
            fp16=False,
            verbose=False,
        )
        try:
            result = future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            print(f"[DEBUG] ⚠️ Segment {segment['index'] + 1} timed out after {timeout_seconds}s")
            executor.shutdown(wait=False, cancel_futures=True)
            return {
                "index": segment["index"],
                "text": "",
                "segments": [],
                "start_time": segment["start_time"],
                "duration": segment.get("duration", 0),
                "error": f"Transcription timed out after {timeout_seconds}s"
            }
        finally:
            executor.shutdown(wait=False)
```

**Timeout 계산**: `max(segment_duration * 0.5, 300)` = 최소 5분, 세그먼트 길이 비례

> **Critic Fix #2**: `with ThreadPoolExecutor` 대신 명시적 `executor.shutdown(wait=False)`를 사용하여
> timeout 시 blocking을 방지함. `cancel_futures=True`는 Python 3.9+에서 지원.

### TODO 2b: Import at top of file

**File**: `audio_processor.py` (top-level imports)

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
```

---

## Phase 3: Background Thread Processing (app.py)

### TODO 3a: Module-level worker registry

**File**: `app.py` (top-level, after imports)

**Add**:
```python
import threading
import time

# Module-level worker registry (survives Streamlit reruns, not serialized)
_active_workers: dict[str, threading.Thread] = {}
```

### TODO 3b: Refactor process_audio_file to use background thread

**File**: `app.py:329-429` (replace `process_audio_file` function)

**Before**: 동기 블로킹 함수 (100 lines)

**After**:
```python
def process_audio_file(uploaded_file, manual_notes: str):
    """Start audio processing in background thread."""
    upload_path = Config.UPLOAD_DIR / uploaded_file.name
    with open(upload_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    is_valid, error_msg = validate_audio_file(upload_path)
    if not is_valid:
        st.error(f"❌ {error_msg}")
        return

    # Critic Fix #3: Extract uploaded_file.name before thread start.
    # UploadedFile is tied to Streamlit session widget state and may become
    # invalid after st.rerun(). Capture the name as a plain string.
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

            # Done - Critic Fix #4: Set all data fields BEFORE setting status="done"
            # status="done" is the signal the polling UI reads, so it must be last.
            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "완료!"
            progress_state["status"] = "done"  # LAST write (polling UI trigger)
            print(f"[DEBUG] === 전체 파이프라인 완료 ==="); sys.stdout.flush()

        except Exception as e:
            print(f"[DEBUG] ❌ 파이프라인 예외: {type(e).__name__}: {e}"); sys.stdout.flush()
            progress_state["error"] = str(e)
            progress_state["status"] = "error"  # LAST write
            upload_path.unlink(missing_ok=True)
        finally:
            # Critic minor fix: use try/except instead of `in dir()` check
            try:
                if audio_processor:
                    audio_processor.cleanup()
            except Exception:
                pass

    thread = threading.Thread(target=background_work, daemon=True)
    _active_workers[worker_id] = thread
    thread.start()
    st.rerun()
```

### TODO 3c: Status-driven polling UI in main()

**File**: `app.py:245-308` (modify `main` function)

**Before** (line 306-307):
```python
    if st.session_state.meeting_minutes:
        display_results()
```

**After** (replace with polling logic):
```python
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
            progress_bar = st.progress(state["progress"])
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
```

### Scope Note: `process_transcript_file` (Critic Fix #5)

`process_transcript_file` (`app.py:122-191`)은 이번 수정 범위에서 **제외**합니다.
- Whisper 없이 TXT → Gemini → Notion 파이프라인만 실행
- 총 소요 시간: ~30초 (Gemini 10-30초 + Notion 2-5초)
- Streamlit WebSocket 타임아웃(~60초)보다 짧아 문제 없음
- 추후 Gemini 응답이 느려질 경우 별도 이슈로 처리

### TODO 3d: Streamlit server config

**File**: `.streamlit/config.toml` (new file)

```toml
[server]
maxUploadSize = 500
enableWebsocketCompression = false
maxMessageSize = 200
```

### TODO 3e: Tests

**File**: `tests/behavior/test_full_workflow_behavior.py` (기존 파일에 추가)

```python
class TestBackgroundProcessing:
    """Background thread processing preserves progress state."""

    def test_progress_state_initialized_on_start(self):
        """process_audio_file sets progress_state in session_state."""

    def test_worker_cleanup_on_completion(self):
        """Worker is removed from _active_workers on done."""

    def test_worker_cleanup_on_error(self):
        """Worker is removed from _active_workers on error."""
```

---

## Files Changed Summary

| File | Phase 1 | Phase 2 | Phase 3 | Changes |
|------|---------|---------|---------|---------|
| `audio_processor.py` | ✅ | ✅ | - | Constants, _segment_audio, _transcribe_segment, _merge_transcripts |
| `app.py` | - | - | ✅ | imports, _active_workers, process_audio_file, main polling |
| `.streamlit/config.toml` | - | - | ✅ | New file (server config) |
| `tests/behavior/test_audio_long_behavior.py` | ✅ | - | - | TestShortFinalSegment class |
| `tests/behavior/test_full_workflow_behavior.py` | - | - | ✅ | TestBackgroundProcessing class |

---

## Acceptance Criteria

### Phase 1: Short Segment Fix
- [ ] 60.5분 오디오 입력 시 세그먼트가 2개 생성됨 (3개가 아님)
- [ ] 마지막 세그먼트가 MIN_SEGMENT_DURATION(60s) 이상일 때는 병합 안 함
- [ ] `_merge_transcripts`에서 짧은 세그먼트 텍스트가 유실되지 않음
- [ ] 기존 37개 테스트 전부 통과
- [ ] 새 테스트 3개 통과

### Phase 2: Transcribe Timeout
- [ ] `model.transcribe()`가 timeout 초과 시 빈 결과 반환 (hang 없음)
- [ ] timeout = max(segment_duration * 0.5, 300초)
- [ ] 정상 전사 시 기존 동작과 동일

### Phase 3: Background Thread
- [ ] 15분+ 처리 중 progress bar가 유지됨 (WebSocket rerun에도 복원)
- [ ] 브라우저 탭을 닫았다 열어도 진행 상태 표시
- [ ] 처리 완료 시 결과가 session_state에 정상 전달
- [ ] 에러 발생 시 에러 메시지 + transcript 경로 표시
- [ ] thread 비정상 종료 시 무한 polling 없음 (safety check)
- [ ] 기존 37개 테스트 전부 통과

### Phase 4: E2E Verification
- [ ] Windows 서버에서 60분+ 오디오 파일 처리 완료
- [ ] 처리 중 progress bar 유지 확인
- [ ] Notion 페이지 정상 생성
- [ ] 텔레그램 알림 정상 수신

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| threading.Thread 참조가 Streamlit 직렬화에 걸림 | Thread 참조 손실 | 모듈-레벨 `_active_workers` dict 사용, session_state에는 worker_id(str)만 저장 |
| dict mutation race condition | 일관성 없는 상태 읽기 | background thread만 write, main thread만 read. `status` 필드를 항상 **마지막에** write하여 polling UI가 일관된 상태를 읽도록 보장 (Critic Fix #4) |
| UploadedFile 참조가 rerun 후 무효화 | 파일명 접근 시 에러 | `file_name = uploaded_file.name`을 thread 시작 전 캡처 (Critic Fix #3) |
| daemon thread 강제 종료 시 GPU 메모리 누수 | VRAM 점유 | `finally` 블록에서 `audio_processor.cleanup()` 호출 (try/except로 안전하게) |
| Streamlit 1.29.0 rerun 오버헤드 | 서버 부하 | Whisper 단계 5초, 나머지 1초 간격으로 polling 조절 |
| ThreadPoolExecutor timeout이 thread를 실제로 종료하지 않음 | zombie thread 잔존 | `executor.shutdown(wait=False, cancel_futures=True)` 사용 (Critic Fix #2). zombie thread는 서버 재시작으로 해소 |

---

## Estimated Commits

```
1. test: Add short final segment and overlap trimming tests
2. fix: Merge short final segment into previous to prevent GPU hang
3. fix: Add timeout safety net to Whisper transcribe
4. feat: Background thread processing with status-driven polling UI
5. chore: Add Streamlit server config
```

---

## Critic Review Changelog (v1)

| # | Issue | Fix Applied |
|---|-------|-------------|
| 1 | `_segment_audio` merge code: `waveform` scope dependency unclear | Added NOTE comment about scope + simplified `extended_end = total_samples` |
| 2 | `ThreadPoolExecutor` `with` block hangs on timeout (`shutdown(wait=True)`) | Replaced `with` block → explicit `executor.shutdown(wait=False, cancel_futures=True)` |
| 3 | `uploaded_file` object not thread-safe after `st.rerun()` | Extract `file_name = uploaded_file.name` and `notes_text` before thread start |
| 4 | `dict.update()` for status transition not atomic → partial read | Set `status = "done"` as the **last** individual write after all data fields |
| 5 | `process_transcript_file` not addressed | Added scope note: excluded (total ~30s, within WebSocket timeout) |
| minor | `'audio_processor' in dir()` unreliable in nested function | Changed to `audio_processor = None` + `try/except` pattern |
| minor | Test stubs lack fixture strategy | Added `_create_silent_wav()` helper + full test bodies with synthetic audio |
