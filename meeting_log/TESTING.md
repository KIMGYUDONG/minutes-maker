# 기능 테스트 가이드

음성 전사는 이미 검증되었으므로, 나머지 핵심 기능(LLM 처리, Notion 연동)만 테스트합니다.

## 📋 테스트 스크립트 목록

### 1. `test_llm_only.py` - LLM 단독 테스트
**목적**: 전사본 → 회의록 생성 기능 검증

**테스트 내용**:
- ✅ Gemini API 연결
- ✅ 회의록 4개 섹션 생성 (Summary, Key Updates, Discussion Log, Action Items)
- ✅ 한국어 처리
- ✅ 전사본 + 수동 메모 병합

**실행 방법** (Windows PC):
```bash
cd C:\code\minutes_maker\meeting_log
python test_llm_only.py
```

**예상 출력**:
```
=== LLM Processor Test ===

1. Initializing LLM Processor...
✅ LLM Processor initialized

2. Generating meeting minutes...
✅ Meeting minutes generated

============================================================
SUMMARY:
============================================================
신규 프로젝트 일정과 리소스 배정에 대한 회의...

============================================================
KEY UPDATES:
============================================================
- 기획안 80% 완료...

✅ Test completed successfully!
```

**소요 시간**: ~30초

---

### 2. `test_notion_only.py` - Notion 단독 테스트
**목적**: 회의록 → Notion 페이지 생성 기능 검증

**테스트 내용**:
- ✅ Notion API 연결
- ✅ 페이지 생성 및 URL 반환
- ✅ 4개 섹션 블록 생성
- ✅ 액션 아이템 체크박스 변환
- ✅ Discussion Log 토글 블록 생성

**실행 방법** (Windows PC):
```bash
cd C:\code\minutes_maker\meeting_log
python test_notion_only.py
```

**예상 출력**:
```
=== Notion Integration Test ===

1. Initializing Notion Client...
✅ Notion Client initialized

2. Creating Notion page...
✅ Notion page created successfully!

============================================================
NOTION PAGE URL:
============================================================
https://www.notion.so/Meeting-Minutes-2025-11-21-14-30-...

============================================================
VERIFICATION:
============================================================
1. Open the URL above in your browser
2. Check that the page has 4 sections:
   - 📝 Summary
   - 🔑 Key Updates
   - 💬 Discussion Log (in toggle block)
   - ✅ Action Items (as checkboxes)
3. Verify the content matches the sample data

✅ Test completed successfully!
```

**소요 시간**: ~5초

**검증 방법**:
1. 출력된 URL을 브라우저에서 열기
2. Notion 페이지 구조 확인:
   - Summary 섹션이 있는지
   - Key Updates가 불릿 리스트로 표시되는지
   - Discussion Log가 접을 수 있는 토글로 되어있는지
   - Action Items가 체크박스로 표시되는지

---

### 3. `test_full_workflow.py` - 전체 워크플로우 테스트
**목적**: 전사본 → LLM → Notion 전체 파이프라인 검증

**테스트 내용**:
- ✅ 전체 워크플로우 (오디오 전사 제외)
- ✅ LLM 처리 후 Notion 업로드
- ✅ 단계별 진행 상황 표시
- ✅ 상세 결과 출력 옵션

**실행 방법** (Windows PC):
```bash
cd C:\code\minutes_maker\meeting_log
python test_full_workflow.py
```

**예상 출력**:
```
================================================================================
=== FULL WORKFLOW TEST: Transcript → LLM → Notion ===
================================================================================

STEP 1: Generate Meeting Minutes with LLM
--------------------------------------------------------------------------------
1-1. Initializing LLM Processor...
     ✅ LLM Processor initialized
1-2. Generating meeting minutes from transcript...
     ✅ Meeting minutes generated

     📄 Generated Sections:
        - Summary: 145 chars
        - Key Updates: 203 chars
        - Discussion Log: 487 chars
        - Action Items: 298 chars

STEP 2: Export to Notion
--------------------------------------------------------------------------------
2-1. Initializing Notion Client...
     ✅ Notion Client initialized
2-2. Creating Notion page...
     ✅ Notion page created successfully!

================================================================================
✅ FULL WORKFLOW COMPLETED SUCCESSFULLY!
================================================================================

📝 Notion Page URL: https://www.notion.so/...

🔍 Verification Steps:
   1. Open the URL above in your browser
   2. Verify the page has proper structure
   3. Check all 4 sections are present and formatted correctly
   4. Verify action items are checkboxes

Print detailed meeting minutes? (y/n):
```

**소요 시간**: ~40초

---

## 🔧 사전 요구사항

### 1. 환경 변수 설정 (.env 파일)

테스트 실행 전 `.env` 파일에 다음 항목이 설정되어 있어야 합니다:

```env
# Gemini API Key (test_llm_only.py, test_full_workflow.py 필요)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-1.5-pro-latest

# Notion Integration (test_notion_only.py, test_full_workflow.py 필요)
NOTION_TOKEN=your_notion_integration_token_here
NOTION_PAGE_ID=your_notion_page_id_here
```

### 2. API 키 확인 방법

**Gemini API Key**:
1. https://makersuite.google.com/app/apikey 접속
2. API 키 생성 또는 기존 키 복사
3. `.env` 파일의 `GEMINI_API_KEY`에 붙여넣기

**Notion Token & Page ID**:
1. https://www.notion.so/my-integrations 접속
2. 새 Integration 생성 또는 기존 Integration 선택
3. "Internal Integration Token" 복사 → `NOTION_TOKEN`
4. Notion에서 회의록을 저장할 페이지 열기
5. URL에서 페이지 ID 복사 (예: `https://notion.so/workspace/26c50cb08d24...` → `26c50cb08d24...`)
6. 해당 페이지에 Integration 연결 (Share → Invite → Integration 선택)

---

## 📊 테스트 시나리오별 실행 가이드

### 시나리오 1: LLM만 빠르게 확인 (30초)
```bash
python test_llm_only.py
```
**목적**: Gemini API 연결 및 회의록 생성 확인

---

### 시나리오 2: Notion만 빠르게 확인 (5초)
```bash
python test_notion_only.py
```
**목적**: Notion API 연결 및 페이지 생성 확인
**검증**: 브라우저에서 생성된 URL 열어서 구조 확인

---

### 시나리오 3: 전체 파이프라인 확인 (40초)
```bash
python test_full_workflow.py
```
**목적**: 전사본 → LLM → Notion 전체 흐름 확인
**검증**: Notion 페이지에서 최종 결과 확인

---

## ❌ 트러블슈팅

### 1. Gemini API 에러

**에러**: `404 models/gemini-pro is not found`
**원인**: 모델 이름이 잘못되었거나 더 이상 지원되지 않음
**해결**:
```bash
# 사용 가능한 모델 확인
python tools/list_models.py

# .env 파일 수정
GEMINI_MODEL_NAME=gemini-1.5-pro-latest
```

**에러**: `401 Unauthorized`
**원인**: API 키가 잘못되었거나 만료됨
**해결**: `.env`의 `GEMINI_API_KEY` 재확인

---

### 2. Notion API 에러

**에러**: `401 Unauthorized`
**원인**: Notion Token이 잘못되었음
**해결**: `.env`의 `NOTION_TOKEN` 재확인

**에러**: `404 object_not_found`
**원인**:
- Page ID가 잘못되었음
- Integration이 페이지에 연결되지 않음

**해결**:
1. Notion 페이지 URL에서 정확한 Page ID 복사
2. 해당 페이지에서 Share → Invite → Integration 연결 확인

**에러**: `403 Forbidden`
**원인**: Integration에 쓰기 권한이 없음
**해결**: Integration 설정에서 "Content Capabilities" → "Insert content" 권한 확인

---

### 3. Python 모듈 에러

**에러**: `ModuleNotFoundError: No module named 'google'`
**원인**: 필요한 패키지가 설치되지 않음
**해결**:
```bash
# 가상환경 활성화
cd C:\code\minutes_maker\meeting_log
venv\Scripts\activate

# 패키지 재설치
pip install -r requirements.txt
```

---

## 📈 성공 기준

모든 테스트가 성공하면 다음을 확인할 수 있습니다:

✅ **LLM 처리 정상 작동**:
- Gemini API 연결 성공
- 한국어 전사본 → 회의록 변환 성공
- 4개 섹션 모두 생성됨

✅ **Notion 연동 정상 작동**:
- Notion API 연결 성공
- 페이지 생성 및 URL 반환
- 올바른 블록 구조 (헤딩, 불릿, 토글, 체크박스)

✅ **전체 파이프라인 정상 작동**:
- 전사본 → LLM → Notion 전체 흐름 성공
- 최종 Notion 페이지에서 결과 확인 가능

---

## 🎯 다음 단계

테스트가 모두 성공하면:

1. **실제 오디오 파일로 전체 테스트**:
   - Streamlit 앱 실행 (`start.bat`)
   - 실제 음성 파일 업로드
   - 전체 파이프라인 확인

2. **pytest 유닛 테스트 작성** (선택):
   - 엣지 케이스 커버리지
   - CI/CD 통합
   - 자동화된 테스트 실행

3. **에러 처리 개선**:
   - 테스트 중 발견된 에러 케이스 처리
   - 사용자 친화적 에러 메시지 추가

---

## 📞 지원

테스트 중 문제가 발생하면:
1. 에러 메시지 전체 복사
2. `.env` 파일 확인 (API 키 제외)
3. `python --version` 확인 (3.10+ 필요)
4. 가상환경 활성화 확인
