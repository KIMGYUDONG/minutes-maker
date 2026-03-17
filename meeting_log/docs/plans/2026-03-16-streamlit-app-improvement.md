# Meeting Minutes Maker - Streamlit 앱 종합 개선 계획

**작성일:** 2026-03-16
**범위:** 17개 이슈 (Critical 2, Major 8, Minor 7)
**예상 복잡도:** MEDIUM-HIGH
**수정 파일:** 6개 (app.py, 1_bridge_minutes.py, 2_soomgo_minutes.py, telegram_notify.py, whisper_client.py, utils.py)

---

## Context

Meeting Minutes Maker는 Streamlit 기반 멀티 페이지 앱으로, 음성 파일을 업로드하면 Whisper 전사 -> Gemini Pro 회의록 생성 -> Notion 저장 -> Telegram 알림 파이프라인을 수행한다.

5개 전문 에이전트 분석 결과 17개 이슈가 식별되었으며, 이를 4단계(Phase)로 나누어 의존성과 리스크 순서로 해결한다.

---

## Work Objectives

1. 안전성 강화: traceback 노출 제거, 불필요한 코드 정리
2. Soomgo 페이지 백그라운드 처리 적용 (Bridge 패턴 추출)
3. 사용자 제어권 확보: Notion 저장 전 확인, 취소 버튼, LLM 실패 복구
4. UX 폴리시: 언어 통일, 랜딩 페이지 개선, 진행률 개선, 헬스체크

---

## Guardrails

### Must Have
- 모든 Phase는 기존 behavior 테스트 37개 통과 유지
- Tidy First 원칙: 구조 변경과 동작 변경을 같은 커밋에 섞지 않음
- 한국어 UI, 영어 코드/주석/커밋 메시지
- 각 Phase 완료 후 `pytest tests/behavior/ -v` 통과 확인

### Must NOT Have
- 불필요한 추상화 (공통 모듈 추출 등 과도한 리팩토링)
- Mock 테스트 추가 (실제 API 테스트만 사용)
- 아키텍처 재설계 (기존 패턴 유지)

---

## Task Flow Diagram

```
Phase 1 (Quick Wins & Safety)          Phase 2 (Soomgo Background)
┌─────────────────────────┐            ┌──────────────────────────┐
│ 1a. traceback 제거       │            │ 2a. Soomgo 백그라운드 처리 │
│ 1b. 죽은 코드 정리       │──순차──>   │     (Bridge 패턴 적용)     │
│ 1c. 언어 통일 (한국어)    │            └───────────┬──────────────┘
│ 1d. CSS 정리             │                        │
│ 1e. 터미널 명령어 제거    │                        │ 순차
└─────────────────────────┘                        ▼
     (1a-1e 내부는 병렬)            Phase 3 (User Control)
                                   ┌──────────────────────────┐
                                   │ 3a. Notion 저장 전 확인    │
                                   │ 3b. LLM 실패 시 전사 복구  │──(3a, 3b 병렬)
                                   │ 3c. 취소 버튼              │──(3c는 3a 후 순차)
                                   └───────────┬──────────────┘
                                               │ 순차
                                               ▼
                                   Phase 4 (Polish)
                                   ┌──────────────────────────┐
                                   │ 4a. Whisper 헬스체크       │
                                   │ 4b. 진행률 개선            │──(4a-4d 병렬)
                                   │ 4c. Telegram 실패 UI 표시  │
                                   │ 4d. 랜딩 페이지 개선       │
                                   └──────────────────────────┘
```

---

## Phase 1: Quick Wins & Safety Fixes

**목적:** 저위험 독립 변경 — traceback 제거, 죽은 코드 정리, 언어 통일
**의존성:** 없음 (독립 실행 가능)
**예상 커밋:** 5개 (각 TODO별 1개)

---

### TODO 1a: Traceback 노출 제거 [M6]

**파일:** `pages/1_bridge_minutes.py` (L148-149), `pages/2_soomgo_minutes.py` (L187-188), `pages/1_bridge_minutes.py` (L321-322)
**이슈:** `traceback.format_exc()`가 사용자에게 full stack trace를 노출 (보안 + UX)
**변경:** traceback을 서버 로그로만 출력하고, UI에는 사용자 친화적 메시지만 표시

**Before** (`pages/1_bridge_minutes.py:144-149`):
```python
    except Exception as llm_error:
        progress_bar.empty()
        st.warning("⚠️ LLM 처리 실패")
        st.error(format_error_message(llm_error))
        st.error("**Details:**")
        st.code(traceback.format_exc())
```

**After:**
```python
    except Exception as llm_error:
        progress_bar.empty()
        st.warning("⚠️ LLM 처리 실패")
        st.error(format_error_message(llm_error))
        print(f"[ERROR] LLM processing failed:\n{traceback.format_exc()}")
```

**Before** (`pages/1_bridge_minutes.py:319-322`):
```python
    except Exception as e:
        st.error(format_error_message(e))
        st.error("**Details:**")
        st.code(traceback.format_exc())
```

**After:**
```python
    except Exception as e:
        st.error(format_error_message(e))
        print(f"[ERROR] Meeting processing failed:\n{traceback.format_exc()}")
```

**Before** (`pages/2_soomgo_minutes.py:185-188`):
```python
    except Exception as e:
        progress_bar.empty()
        st.error(format_error_message(e))
        st.code(traceback.format_exc())
```

**After:**
```python
    except Exception as e:
        progress_bar.empty()
        st.error(format_error_message(e))
        print(f"[ERROR] Soomgo processing failed:\n{traceback.format_exc()}")
```

**검증:** 앱 실행 후 잘못된 파일 업로드 시 traceback이 UI에 표시되지 않고 터미널 로그에만 출력되는지 확인

---

### TODO 1b: 죽은 코드 정리 (processing_id) [Minor]

**파일:** `pages/1_bridge_minutes.py` (L32-59)
**이슈:** `processing_id`와 `clear_previous_results()` 함수가 이전 편집 UI 잔재. 현재 자동 저장 플로우에서 사용되지 않음.

**Before** (`pages/1_bridge_minutes.py:24-59`):
```python
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
```

**After:**
```python
def initialize_session_state():
    """Initialize session state variables."""
    if 'transcript_result' not in st.session_state:
        st.session_state.transcript_result = None
    if 'meeting_minutes' not in st.session_state:
        st.session_state.meeting_minutes = None
    if 'notion_url' not in st.session_state:
        st.session_state.notion_url = None


def clear_previous_results():
    """Clear previous meeting results for new processing."""
    st.session_state.transcript_result = None
    st.session_state.meeting_minutes = None
    st.session_state.notion_url = None
```

**검증:** `processing_id` 문자열이 파일에 존재하지 않는지 grep 확인. `pytest tests/behavior/ -v` 통과.

---

### TODO 1c: 영어/한국어 혼용 UI 통일 [M5]

**파일:** `pages/1_bridge_minutes.py` (다수 위치)
**이슈:** Bridge 페이지에 영어 UI 문자열이 혼재. Soomgo는 이미 한국어로 통일됨.

변경 대상 문자열 (모두 `pages/1_bridge_minutes.py`):

| 라인 | Before (영어) | After (한국어) |
|------|--------------|---------------|
| L86 | `"⏳ Transcript 파일 로드 중..."` | `"⏳ 텍스트 파일 로드 중..."` |
| L107 | `"⏳ Generating meeting minutes with Gemini..."` | `"⏳ Gemini로 회의록 생성 중..."` |
| L166 | `"### 📋 Meeting Minutes Generator"` | `"### 📋 회의록 생성기"` |
| L175 | `"#### ℹ️ How to Use"` | `"#### ℹ️ 사용 방법"` |
| L176-182 | 영어 사용 가이드 | 한국어 사용 가이드 |
| L185 | `"#### ⚙️ System Info"` | `"#### ⚙️ 시스템 정보"` |
| L215 | `'📋 Automated Meeting Minutes'` | `'📋 회의록 자동 생성'` |
| L216 | `"Transform your meeting..."` | `"회의 녹음을 AI로 구조화된 회의록으로 변환합니다"` |
| L230 | `'📁 File Upload'` | `'📁 파일 업로드'` |
| L231 | `"Upload audio or transcript file"` | `"음성 또는 텍스트 파일 업로드"` |
| L242 | `'📝 Manual Notes (Optional)'` | `'📝 수기 노트 (선택)'` |
| L243 | `"Add your manual notes here"` | `"수기 노트 입력"` |
| L245 | `"Paste or type..."` | `"미팅 중 메모한 내용..."` |
| L246 | `"These notes will be merged..."` | `"음성 전사와 합쳐져 회의록이 생성됩니다"` |
| L253 | `"🚀 Generate Meeting Minutes"` | `"🚀 회의록 생성"` |
| L263 | `"👆 Please upload an audio..."` | `"👆 음성 또는 텍스트 파일을 업로드하세요"` |
| L289 | `"⏳ {state['message']}"` | (message 자체를 한국어화 - background_work 내부) |
| L294 | `"Processing failed unexpectedly..."` | `"처리 중 예기치 않은 오류가 발생했습니다. 서버 로그를 확인하세요."` |
| L344 | `"Initializing audio processor..."` | `"오디오 프로세서 초기화 중..."` |
| L391 | `"Generating meeting minutes with Gemini Pro..."` | `"Gemini Pro로 회의록 생성 중..."` |

**검증:** 앱 실행 후 Bridge 페이지에서 영어 UI 문자열이 없는지 육안 확인

---

### TODO 1d: CSS 정리 [Minor - 미사용 클래스 + WCAG 색상]

**파일:** `app.py` (L12-48)
**이슈:** `.status-box`, `.success-box`, `.error-box`, `.info-box` 클래스가 어디에서도 사용되지 않음. `#1f77b4` 색상은 WCAG AA 미달 (contrast 3.4:1).

**Before** (`app.py:12-48`):
```python
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
```

**After:**
```python
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1565C0;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)
```

> `#1565C0`은 흰색 배경 대비 WCAG AA 통과 (contrast 5.6:1)

**검증:** 미사용 CSS 클래스가 코드에서 완전히 제거되었는지 grep 확인. 각 페이지에서 스타일 깨짐 없는지 확인.

---

### TODO 1e: 터미널 명령어 노출 제거 [Minor]

**파일:** `pages/1_bridge_minutes.py` (L457)
**이슈:** 프로덕션 UI에 개발자용 터미널 명령어가 노출됨

**Before** (`pages/1_bridge_minutes.py:457`):
```python
    st.info("💡 터미널에서 `cd bridge && claude` 실행 후 `/linear` 입력하여 Linear 이슈를 등록하세요")
```

**After:**
```python
    st.info("💡 회의록 확인 후 필요한 액션 아이템을 등록해주세요")
```

**검증:** `display_results()` 함수에 `cd bridge`, `claude`, `/linear` 문자열이 없는지 확인

---

## Phase 1 Files Changed Summary

| 파일 | TODO 1a | TODO 1b | TODO 1c | TODO 1d | TODO 1e |
|------|---------|---------|---------|---------|---------|
| `app.py` | | | | **수정** | |
| `pages/1_bridge_minutes.py` | **수정** | **수정** | **수정** | | **수정** |
| `pages/2_soomgo_minutes.py` | **수정** | | | | |

### Phase 1 Acceptance Criteria
- [ ] `grep -r "traceback.format_exc" pages/` 결과에서 `st.code()` 호출 없음
- [ ] `grep -r "processing_id" pages/` 결과 없음
- [ ] Bridge 페이지에서 영어 UI 문자열 0개 (sidebar 포함)
- [ ] `grep -r "status-box\|success-box\|error-box\|info-box" app.py` 결과 없음
- [ ] `grep -r "cd bridge\|/linear" pages/` 결과 없음
- [ ] `pytest tests/behavior/ -v` — 37개 통과

---

## Phase 2: Soomgo 백그라운드 처리 [M1]

**목적:** Soomgo 페이지에 Bridge와 동일한 백그라운드 스레드 처리 패턴 적용
**의존성:** Phase 1 완료 후 (코드 정리된 상태에서 작업)
**예상 커밋:** 2개 (리팩토링 1, 기능 변경 1)

---

### TODO 2a: Soomgo 동기 처리를 백그라운드 스레드로 전환

**파일:** `pages/2_soomgo_minutes.py` (전면 수정)
**이슈:** `process_soomgo_meeting()` 함수가 동기적으로 실행되어 Streamlit 메인 스레드를 블로킹. 세션 타임아웃 위험. Bridge에서는 이미 해결된 동일 문제.

**적용 패턴:** `pages/1_bridge_minutes.py`의 `process_audio_file()` + polling UI 패턴을 Soomgo에 적용

**Before** (`pages/2_soomgo_minutes.py:96-188`, 핵심 구조):
```python
def process_soomgo_meeting(
    uploaded_file, client_name, meeting_type, industry, user_name, manual_notes
):
    """Process uploaded file through Whisper → Gemini → Notion pipeline."""
    progress_bar = st.progress(0)
    status = st.empty()

    try:
        # ... 동기 처리 (Whisper → LLM → Notion → Telegram) ...
        # Streamlit 메인 스레드에서 직접 실행 → UI 프리즈
        st.rerun()

    except Exception as e:
        progress_bar.empty()
        st.error(format_error_message(e))
        print(f"[ERROR] Soomgo processing failed:\n{traceback.format_exc()}")
```

**After** (핵심 구조):
```python
def process_soomgo_meeting(
    uploaded_file, client_name, meeting_type, industry, user_name, manual_notes
):
    """Start Soomgo processing in background thread."""
    Config.setup_directories()
    upload_path = Config.UPLOAD_DIR / uploaded_file.name
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    file_ext = Path(uploaded_file.name).suffix.lower()

    # Capture values before thread start
    file_name = uploaded_file.name
    notes_text = manual_notes.strip() if manual_notes else ""

    progress_state = {
        "phase": "init",
        "message": "초기화 중...",
        "progress": 0.1,
        "status": "running",
        "notion_url": None,
        "error": None,
    }

    worker_id = str(int(time.time() * 1000))
    st.session_state.soomgo_progress_state = progress_state
    st.session_state.soomgo_worker_id = worker_id

    def background_work():
        try:
            # 1. Transcribe
            if file_ext in Config.TEXT_FORMATS:
                progress_state["message"] = "텍스트 파일 로드 중..."
                progress_state["progress"] = 0.3
                transcript_text = Path(upload_path).read_text(encoding="utf-8")
            else:
                is_valid, error_msg = validate_audio_file(upload_path)
                if not is_valid:
                    progress_state["error"] = error_msg
                    progress_state["status"] = "error"
                    return

                progress_state["message"] = "Whisper 서버에 연결 중..."
                progress_state["progress"] = 0.1

                def update_fn(msg):
                    progress_state["message"] = msg

                whisper = WhisperClient(progress_callback=update_fn)
                result = whisper.transcribe(upload_path)
                transcript_text = result["text"]
                progress_state["progress"] = 0.4

            if not transcript_text.strip():
                progress_state["error"] = "음성이 감지되지 않았습니다."
                progress_state["status"] = "error"
                return

            # Save transcript backup
            transcript_path = Config.UPLOAD_DIR / f"{Path(file_name).stem}_transcript.txt"
            transcript_path.write_text(transcript_text, encoding="utf-8")

            # 2. LLM
            progress_state["phase"] = "llm"
            progress_state["message"] = "Gemini로 회의록 생성 중..."
            progress_state["progress"] = 0.5
            llm = LLMProcessor()
            minutes = llm.create_sales_meeting_minutes(
                transcript=transcript_text,
                client_name=client_name,
                manual_notes=notes_text if notes_text else None,
            )

            # 3. Notion
            progress_state["phase"] = "notion"
            progress_state["message"] = "노션에 저장 중..."
            progress_state["progress"] = 0.7
            notion = NotionClient()
            url = notion.create_soomgo_minutes(
                content=minutes["content"],
                client_name=client_name,
                meeting_type=meeting_type,
                industry=industry,
                user_name=user_name,
                ai_summary=minutes.get("ai_summary", ""),
            )
            progress_state["notion_url"] = url

            # 4. Telegram
            progress_state["phase"] = "telegram"
            progress_state["message"] = "텔레그램 알림 전송 중..."
            progress_state["progress"] = 0.9
            send_telegram_notification_to_user(
                user_name=user_name, notion_url=url, client_name=client_name,
            )

            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "완료!"
            progress_state["status"] = "done"

        except Exception as e:
            print(f"[ERROR] Soomgo pipeline failed: {type(e).__name__}: {e}")
            progress_state["error"] = str(e)
            progress_state["status"] = "error"
            upload_path.unlink(missing_ok=True)

    thread = threading.Thread(target=background_work, daemon=True)
    active_workers[worker_id] = thread
    thread.start()
    st.rerun()
```

**main() 함수에 polling UI 추가:**
```python
    # Active processing: show polling UI
    worker_id = st.session_state.get("soomgo_worker_id")
    if worker_id and st.session_state.get("soomgo_progress_state"):
        state = st.session_state.soomgo_progress_state

        if state["status"] == "done":
            st.session_state.soomgo_notion_url = state.get("notion_url")
            st.session_state.soomgo_worker_id = None
            active_workers.pop(worker_id, None)
            st.rerun()

        elif state["status"] == "error":
            st.error(f"❌ {state['error']}")
            st.session_state.soomgo_worker_id = None
            active_workers.pop(worker_id, None)

        else:
            st.progress(state["progress"])
            status_text = st.empty()
            status_text.info(f"⏳ {state['message']}")

            thread = active_workers.get(worker_id)
            if thread and not thread.is_alive() and state["status"] == "running":
                st.error("처리 중 예기치 않은 오류가 발생했습니다.")
                st.session_state.soomgo_worker_id = None
                active_workers.pop(worker_id, None)
            else:
                poll_interval = 5 if state["progress"] < 0.5 else 1
                time.sleep(poll_interval)
                st.rerun()
```

**추가 import 필요:**
```python
import threading
import time
from worker_registry import active_workers
```

**검증:**
1. Soomgo 페이지에서 오디오 파일 업로드 후 처리 시작 -> UI가 프리즈되지 않고 진행률 표시
2. 처리 완료 후 노션 URL 정상 표시
3. 브라우저 탭을 닫았다 열어도 세션 상태 유지
4. `pytest tests/behavior/ -v` 통과

---

## Phase 2 Files Changed Summary

| 파일 | TODO 2a |
|------|---------|
| `pages/2_soomgo_minutes.py` | **전면 수정** (동기 → 비동기) |

### Phase 2 Acceptance Criteria
- [ ] `process_soomgo_meeting()` 내부에 `st.progress()`, `st.empty()` 직접 호출 없음 (백그라운드 스레드에서 st 호출 불가)
- [ ] `soomgo_worker_id`, `soomgo_progress_state` 세션 상태 사용
- [ ] Soomgo 페이지 처리 중 UI 반응성 유지 (polling으로 진행률 갱신)
- [ ] `pytest tests/behavior/ -v` — 37개 통과

---

## Phase 3: User Control Improvements

**목적:** 사용자가 Notion 저장 전 확인하고, 처리 취소 가능하며, LLM 실패 시 전사 결과를 복구할 수 있도록 개선
**의존성:** Phase 2 완료 후 (Soomgo도 백그라운드 처리 상태에서 작업)
**예상 커밋:** 3개

---

### TODO 3a: Notion 저장 전 사용자 확인 [C1]

**파일:** `pages/1_bridge_minutes.py` (background_work 내 Notion 자동 저장 로직), `pages/2_soomgo_minutes.py` (동일)
**이슈:** LLM 결과가 사용자 검토 없이 곧바로 Notion에 저장됨

**핵심 전략:**
- background_work에서 LLM까지만 수행하고, Notion 저장은 하지 않음
- LLM 완료 후 `status="review"` 상태로 전환
- UI에서 사용자가 결과를 확인하고 "노션에 저장" 버튼 클릭 시 Notion 저장 + Telegram 알림 수행

**Before** (Bridge `background_work` 내부, L401-427):
```python
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

            # Phase: Telegram
            progress_state["phase"] = "telegram"
            progress_state["message"] = "텔레그램 알림 전송 중..."
            progress_state["progress"] = 0.9
            send_telegram_notification(url)

            # Done
            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "완료!"
            progress_state["status"] = "done"
```

**After** (background_work에서 LLM까지만 수행):
```python
            # LLM done — pause for user review
            upload_path.unlink(missing_ok=True)
            progress_state["progress"] = 1.0
            progress_state["message"] = "회의록 생성 완료 — 확인 후 저장해주세요"
            progress_state["status"] = "review"
```

**UI 변경** (Bridge `main()` 내 polling UI에 "review" 상태 핸들링 추가):
```python
        if state["status"] == "review":
            # Transfer minutes to session for display
            st.session_state.meeting_minutes = state.get("minutes")
            st.session_state.worker_id = None
            active_workers.pop(worker_id, None)
            st.rerun()
```

**`display_results()` 함수를 편집+확인 UI로 변경:**

**Before** (`pages/1_bridge_minutes.py:447-458`):
```python
def display_results():
    """Display completion message after auto-save to Notion."""
    st.markdown("---")
    st.markdown('<div class="section-header">✅ 완료</div>', unsafe_allow_html=True)

    st.success("회의록이 노션에 자동 저장되었습니다!")

    if st.session_state.notion_url:
        st.markdown(f"### 📎 [노션에서 보기]({st.session_state.notion_url})")

    st.info("💡 회의록 확인 후 필요한 액션 아이템을 등록해주세요")
```

**After:**
```python
def display_results():
    """Display minutes for review and provide save-to-Notion button."""
    minutes = st.session_state.meeting_minutes
    st.markdown("---")

    if st.session_state.notion_url:
        # Already saved
        st.markdown('<div class="section-header">✅ 완료</div>', unsafe_allow_html=True)
        st.success("회의록이 노션에 저장되었습니다!")
        st.markdown(f"### 📎 [노션에서 보기]({st.session_state.notion_url})")
        st.info("💡 회의록 확인 후 필요한 액션 아이템을 등록해주세요")
        return

    # Preview generated minutes
    st.markdown('<div class="section-header">📝 회의록 미리보기</div>', unsafe_allow_html=True)
    st.info("아래 내용을 확인 후 노션에 저장하세요.")

    with st.expander("요약", expanded=True):
        st.markdown(minutes.get('summary', ''))
    with st.expander("업데이트", expanded=True):
        st.markdown(minutes.get('key_updates', ''))
    with st.expander("논의사항", expanded=True):
        st.markdown(minutes.get('discussion_log', ''))
    with st.expander("할 일", expanded=True):
        st.markdown(minutes.get('action_items', ''))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 노션에 저장", type="primary", use_container_width=True):
            save_to_notion_bridge(minutes)
    with col2:
        if st.button("🔄 다시 생성", use_container_width=True):
            clear_previous_results()
            st.rerun()


def save_to_notion_bridge(minutes):
    """Save reviewed minutes to Notion and send Telegram notification."""
    with st.spinner("노션에 저장 중..."):
        notion_client = NotionClient()
        url = notion_client.create_meeting_minutes(
            summary=minutes.get('summary', ''),
            key_updates=minutes.get('key_updates', ''),
            discussion_log=minutes.get('discussion_log', ''),
            action_items=minutes.get('action_items', '')
        )
        st.session_state.notion_url = url
        send_telegram_notification(url)
        st.rerun()
```

**Soomgo에도 동일 패턴 적용** (background_work에서 LLM까지만, UI에서 확인 후 저장)

**검증:**
1. 파이프라인 완료 후 UI에 미리보기가 표시됨
2. "노션에 저장" 버튼 클릭 전까지 Notion 페이지가 생성되지 않음
3. 저장 후 노션 URL 링크 표시
4. "다시 생성" 클릭 시 상태 초기화

---

### TODO 3b: LLM 실패 시 전사 결과 복구 [C3]

**파일:** `pages/1_bridge_minutes.py` (background_work 에러 핸들링)
**이슈:** Whisper 전사 완료 후 LLM 실패 시 10-30분의 전사 작업이 무의미해짐. 전사 파일은 이미 저장되지만 (L385-387) UI에서 복구 경로를 제공하지 않음.

**Before** (background_work error 핸들링, L429-433):
```python
        except Exception as e:
            print(f"[DEBUG] ❌ 파이프라인 예외: {type(e).__name__}: {e}"); sys.stdout.flush()
            progress_state["error"] = str(e)
            progress_state["status"] = "error"
            upload_path.unlink(missing_ok=True)
```

**After:**
```python
        except Exception as e:
            print(f"[ERROR] Pipeline failed: {type(e).__name__}: {e}"); sys.stdout.flush()
            progress_state["error"] = str(e)
            progress_state["status"] = "error"
            # Keep transcript_path so user can retry with txt upload
            upload_path.unlink(missing_ok=True)
```

**UI 에러 표시에 복구 안내 추가** (main() 내 polling UI error 상태):

**Before** (`pages/1_bridge_minutes.py:278-283`):
```python
        elif state["status"] == "error":
            st.error(f"❌ {state['error']}")
            if state.get("transcript_path"):
                st.info(f"📁 Transcript 저장됨: `{state['transcript_path']}`")
            st.session_state.worker_id = None
            active_workers.pop(worker_id, None)
```

**After:**
```python
        elif state["status"] == "error":
            st.error(f"❌ {state['error']}")
            if state.get("transcript_path"):
                st.warning(
                    f"💾 전사 결과가 저장되어 있습니다: `{state['transcript_path']}`\n\n"
                    "위 파일을 텍스트 파일(.txt)로 업로드하면 Whisper 단계를 건너뛰고 회의록을 생성할 수 있습니다."
                )
            st.session_state.worker_id = None
            active_workers.pop(worker_id, None)
```

**검증:**
1. LLM API 키를 일시적으로 잘못 설정하여 LLM 실패 유도
2. 에러 발생 시 전사 파일 경로 + 복구 안내 메시지가 UI에 표시되는지 확인
3. 해당 txt 파일을 업로드하면 Whisper 건너뛰고 LLM부터 처리되는지 확인

---

### TODO 3c: 처리 중 취소 버튼 [M3]

**파일:** `pages/1_bridge_minutes.py`, `pages/2_soomgo_minutes.py`
**이슈:** 처리 중 취소 방법이 없어 사용자가 브라우저를 닫아야 함
**의존성:** TODO 3a 이후 (review 상태 추가된 후)

**변경:** polling UI 영역에 "취소" 버튼 추가. 클릭 시 progress_state에 cancel 시그널을 보내고 UI를 초기화.

**Before** (polling UI running 상태, `1_bridge_minutes.py:285-300`):
```python
        else:
            # Running: show progress and poll
            st.progress(state["progress"])
            status_text = st.empty()
            status_text.info(f"⏳ {state['message']}")

            # Safety check: thread alive?
            thread = active_workers.get(worker_id)
            if thread and not thread.is_alive() and state["status"] == "running":
                st.error("처리 중 예기치 않은 오류가 발생했습니다.")
                st.session_state.worker_id = None
                active_workers.pop(worker_id, None)
            else:
                poll_interval = 5 if state["progress"] < 0.5 else 1
                time.sleep(poll_interval)
                st.rerun()
```

**After:**
```python
        else:
            # Running: show progress and poll
            st.progress(state["progress"])
            status_text = st.empty()
            status_text.info(f"⏳ {state['message']}")

            if st.button("❌ 취소", key="cancel_bridge"):
                state["status"] = "cancelled"
                st.session_state.worker_id = None
                active_workers.pop(worker_id, None)
                st.warning("처리가 취소되었습니다.")
                if state.get("transcript_path"):
                    st.info(f"💾 전사 결과: `{state['transcript_path']}`")
                st.rerun()
                return

            # Safety check: thread alive?
            thread = active_workers.get(worker_id)
            if thread and not thread.is_alive() and state["status"] == "running":
                st.error("처리 중 예기치 않은 오류가 발생했습니다.")
                st.session_state.worker_id = None
                active_workers.pop(worker_id, None)
            else:
                poll_interval = 5 if state["progress"] < 0.5 else 1
                time.sleep(poll_interval)
                st.rerun()
```

> 참고: 백그라운드 스레드는 daemon=True이므로 참조를 제거하면 GC에 의해 정리됨. 스레드를 강제 중지하지 않지만, UI에서는 즉시 취소 상태로 전환.

**Soomgo에도 동일 패턴 적용**

**검증:**
1. 처리 진행 중 "취소" 버튼이 표시되는지 확인
2. 취소 클릭 시 UI가 즉시 초기 상태로 돌아가는지 확인
3. Whisper 완료 후 취소 시 전사 파일 경로가 표시되는지 확인

---

## Phase 3 Files Changed Summary

| 파일 | TODO 3a | TODO 3b | TODO 3c |
|------|---------|---------|---------|
| `pages/1_bridge_minutes.py` | **수정** (background_work + display_results + save_to_notion_bridge 추가) | **수정** (에러 UI) | **수정** (취소 버튼) |
| `pages/2_soomgo_minutes.py` | **수정** (동일 패턴) | | **수정** (취소 버튼) |

### Phase 3 Acceptance Criteria
- [ ] Bridge/Soomgo: LLM 완료 후 미리보기 UI 표시, "노션에 저장" 버튼 동작
- [ ] Bridge/Soomgo: "다시 생성" 버튼으로 상태 초기화
- [ ] Bridge: LLM 실패 시 전사 복구 안내 메시지 + txt 재업로드 가능
- [ ] Bridge/Soomgo: 처리 중 취소 버튼 동작
- [ ] `pytest tests/behavior/ -v` — 37개 통과

---

## Phase 4: Polish

**목적:** UX 세부 개선 — 헬스체크, 진행률, 알림, 랜딩 페이지
**의존성:** Phase 3 완료 후
**예상 커밋:** 4개

---

### TODO 4a: Whisper 서버 헬스체크 [M8]

**파일:** `pages/2_soomgo_minutes.py`, `pages/1_bridge_minutes.py`
**이슈:** 처리 시작 전 Whisper 서버 상태를 확인하지 않아, 10분 후 타임아웃으로 실패할 수 있음

**변경:** 처리 시작 전 `WhisperClient.health_check()` 호출. 실패 시 즉시 에러 표시.

**Before** (Bridge `process_audio_file` 시작부, L325-334):
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
```

**After:**
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

    # Pre-flight health check (only for remote Whisper)
    if not HAS_LOCAL_WHISPER:
        try:
            whisper = WhisperClient()
            whisper.health_check()
        except Exception as e:
            st.error(f"❌ Whisper 서버에 연결할 수 없습니다: {e}")
            st.info("서버 상태를 확인한 후 다시 시도해주세요.")
            upload_path.unlink(missing_ok=True)
            return
```

**Soomgo에도 동일 패턴 적용** (background_work 시작 전 호출)

> 참고: WhisperClient에 이미 `health_check()` 메서드가 구현되어 있음 (`whisper_client.py:24-28`)

**검증:**
1. Whisper 서버가 꺼진 상태에서 처리 시작 시 즉시 에러 메시지 표시
2. 서버 정상 시 기존과 동일하게 동작

---

### TODO 4b: time.sleep 개선 [M2]

**파일:** `pages/1_bridge_minutes.py` (L298-299), `pages/2_soomgo_minutes.py` (Phase 2에서 추가된 polling)
**이슈:** `time.sleep(5)` 가 Streamlit 메인 스레드를 5초간 블로킹

**변경:** Whisper 단계(느린)에서 sleep을 3초로 줄이고, LLM/Notion 단계에서는 1초로 줄임. `st_autorefresh`는 외부 의존성이므로 사용하지 않고, 단순히 sleep 시간을 최적화.

**Before** (`pages/1_bridge_minutes.py:298`):
```python
                poll_interval = 5 if state["progress"] < 0.5 else 1
```

**After:**
```python
                poll_interval = 3 if state["progress"] < 0.5 else 1
```

**검증:** Whisper 처리 중 UI 갱신이 3초 간격으로 이루어지는지 확인

---

### TODO 4c: Telegram 알림 실패 UI 표시 [M7]

**파일:** `pages/1_bridge_minutes.py` (save_to_notion_bridge), `pages/2_soomgo_minutes.py`
**이슈:** Telegram 전송 실패가 `print()`로만 로깅되고 사용자에게 알려지지 않음

**변경:** Phase 3에서 Notion 저장이 UI 함수(`save_to_notion_bridge`)로 이동하므로, 여기서 Telegram 반환값을 확인하여 경고 표시.

**After** (`save_to_notion_bridge` 내부, Phase 3 코드에 추가):
```python
def save_to_notion_bridge(minutes):
    """Save reviewed minutes to Notion and send Telegram notification."""
    with st.spinner("노션에 저장 중..."):
        notion_client = NotionClient()
        url = notion_client.create_meeting_minutes(
            summary=minutes.get('summary', ''),
            key_updates=minutes.get('key_updates', ''),
            discussion_log=minutes.get('discussion_log', ''),
            action_items=minutes.get('action_items', '')
        )
        st.session_state.notion_url = url

        telegram_ok = send_telegram_notification(url)
        if not telegram_ok:
            st.session_state.telegram_warning = True

        st.rerun()
```

**display_results() 완료 상태에 경고 추가:**
```python
    if st.session_state.notion_url:
        st.success("회의록이 노션에 저장되었습니다!")
        st.markdown(f"### 📎 [노션에서 보기]({st.session_state.notion_url})")
        if st.session_state.get("telegram_warning"):
            st.warning("⚠️ 텔레그램 알림 전송에 실패했습니다. 수동으로 공유해주세요.")
```

**검증:**
1. Telegram 설정이 잘못된 상태에서 저장 시 경고 메시지 표시
2. Telegram 정상 시 경고 없음

---

### TODO 4d: 랜딩 페이지 개선 [Minor]

**파일:** `app.py` (L50-56)
**이슈:** 랜딩 페이지가 2줄짜리 설명만 있어 너무 빈약함

**Before** (`app.py:50-56`):
```python
st.markdown('<div class="main-header">📋 Meeting Minutes Generator</div>', unsafe_allow_html=True)
st.markdown("Choose a mode from the sidebar.")
st.markdown("""
### Available Modes
- **📋 Bridge 회의록**: 팀 내부 회의 녹음 → 회의록 자동 생성
- **🤝 숨고 클라이언트**: 영업 미팅 녹음 → 클라이언트별 회의록 생성
""")
```

**After:**
```python
st.markdown('<div class="main-header">📋 회의록 생성기</div>', unsafe_allow_html=True)
st.markdown("회의 녹음 파일을 업로드하면 AI가 자동으로 구조화된 회의록을 생성합니다.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📋 Bridge 회의록")
    st.markdown(
        "팀 내부 회의 녹음을 업로드하면 요약, 업데이트, "
        "논의사항, 할 일 목록이 포함된 회의록을 자동 생성하여 노션에 저장합니다."
    )
    st.page_link("pages/1_bridge_minutes.py", label="Bridge 회의록 시작", icon="📋")

with col2:
    st.markdown("### 🤝 숨고 클라이언트")
    st.markdown(
        "영업 미팅 녹음을 업로드하면 고객 현황, 요구사항, "
        "제안 솔루션, 후속 액션이 포함된 미팅 노트를 자동 생성합니다."
    )
    st.page_link("pages/2_soomgo_minutes.py", label="숨고 회의록 시작", icon="🤝")

st.markdown("---")
st.markdown("#### 사용 흐름")
st.markdown(
    "1. 사이드바에서 모드를 선택하거나 위 버튼을 클릭\n"
    "2. 음성 파일(.m4a, .mp3, .wav) 또는 텍스트 파일(.txt) 업로드\n"
    "3. AI가 회의록을 생성하면 내용을 확인\n"
    "4. 노션에 저장하고 텔레그램으로 알림 전송"
)
```

**검증:** 랜딩 페이지에 2열 레이아웃 + 페이지 링크 + 사용 흐름 표시

---

## Phase 4 Files Changed Summary

| 파일 | TODO 4a | TODO 4b | TODO 4c | TODO 4d |
|------|---------|---------|---------|---------|
| `app.py` | | | | **수정** |
| `pages/1_bridge_minutes.py` | **수정** | **수정** | **수정** | |
| `pages/2_soomgo_minutes.py` | **수정** | **수정** | **수정** | |

### Phase 4 Acceptance Criteria
- [ ] Whisper 서버 다운 시 즉시 에러 메시지 (10분 타임아웃 대기 없음)
- [ ] polling 간격 3초/1초로 개선
- [ ] Telegram 실패 시 UI 경고 표시
- [ ] 랜딩 페이지에 2열 모드 선택 + 페이지 링크 + 사용 흐름 표시
- [ ] `pytest tests/behavior/ -v` — 37개 통과

---

## 전체 Files Changed Summary

| 파일 | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|
| `app.py` | CSS 정리 | | | 랜딩 페이지 |
| `pages/1_bridge_minutes.py` | traceback, 죽은코드, 언어, 터미널 | | 확인UI, 복구, 취소 | 헬스체크, sleep, telegram |
| `pages/2_soomgo_minutes.py` | traceback | 백그라운드 처리 | 확인UI, 취소 | 헬스체크, sleep, telegram |
| `telegram_notify.py` | | | | (변경 없음, 호출부만 변경) |
| `whisper_client.py` | | | | (변경 없음, 기존 health_check 활용) |

---

## Success Criteria (전체)

1. **안전성:** 사용자에게 traceback 노출 없음, 터미널 명령어 노출 없음
2. **안정성:** Soomgo 페이지 세션 타임아웃 없음 (백그라운드 처리)
3. **제어권:** Notion 저장 전 미리보기 + 확인, 처리 취소 가능
4. **복구:** LLM 실패 시 전사 결과 복구 경로 제공
5. **일관성:** 전체 UI 한국어 통일, WCAG AA 색상
6. **테스트:** 기존 37개 behavior 테스트 100% 통과 유지

---

## Open Questions

아래 항목들은 `.omc/plans/open-questions.md`에도 기록됨.

1. **Soomgo 미리보기 UI 형식**: Bridge는 4개 섹션(요약/업데이트/논의/할일)이지만 Soomgo는 단일 마크다운 content. 미리보기를 어떤 형식으로 보여줄지 — 단순 마크다운 렌더링으로 충분한지, 아니면 섹션별 분리가 필요한지.

2. **취소 시 백그라운드 스레드 정리**: daemon 스레드는 참조 제거 시 GC 대상이지만, 진행 중인 Whisper HTTP 요청은 timeout(600초)까지 연결을 유지할 수 있음. 명시적 abort가 필요한지.

3. **CSS 주입 위치**: 현재 CSS가 `app.py`에만 있어 직접 페이지 접근 시 스타일 없음. 각 페이지에 CSS를 중복 배치할지, `st.set_page_config` 이후 공통 함수로 호출할지.
