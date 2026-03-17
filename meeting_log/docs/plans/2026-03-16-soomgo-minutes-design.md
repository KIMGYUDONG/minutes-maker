# Soomgo Client Meeting Minutes Automation

## Overview

Extend the existing minutes_maker Streamlit app to support Soomgo client meeting minutes.
Two modes in one app: "Bridge Meeting Minutes" and "Soomgo Client Minutes".

**Date**: 2026-03-16
**Status**: Approved

---

## Architecture

### Pipeline

```
Mac Voice Memo (m4a)
  → Whisper HTTP Server (100.71.112.103:8765, Tailscale internal)
  → Gemini Pro 2.5 (sales meeting prompt)
  → Notion DB (new "숨고 클라이언트 회의록" DB under Bridge)
  → Telegram notification (uploader only)
```

### Hosting

**Mac + Cloudflare Tunnel**
- Streamlit runs on Mac (localhost:8501)
- Cloudflare Tunnel exposes only port 8501 to a public URL
- Teammate accesses via browser (no installation needed)
- Whisper server stays internal (Tailscale only, never exposed)
- Cloudflare provides DDoS/WAF protection automatically

### Streamlit Multipage Structure

```
app.py                          → Main router (simplified)
pages/
  1_bridge_minutes.py           → Existing Bridge meeting minutes (moved from app.py)
  2_soomgo_minutes.py           → New Soomgo client minutes page
```

---

## Changes to Existing Codebase

### New Files

| File | Purpose |
|------|---------|
| `whisper_client.py` | HTTP client for Whisper server (replaces local torch dependency) |
| `pages/1_bridge_minutes.py` | Existing app.py logic moved here |
| `pages/2_soomgo_minutes.py` | Soomgo client minutes UI |

### Modified Files

| File | Changes |
|------|---------|
| `app.py` | Simplify to multipage router (remove current processing logic) |
| `llm_processor.py` | Add `create_sales_meeting_minutes()` with new prompt |
| `notion_integration.py` | Add `create_soomgo_minutes()` for new DB target |
| `telegram_notify.py` | Add per-user chat_id routing |
| `config.py` | Add Soomgo-specific config (Notion DB ID, user chat_ids) |
| `.env.example` | Add new env vars |

### Unchanged Files

| File | Reason |
|------|--------|
| `audio_processor.py` | Keep as-is for Windows local Whisper (backward compatible) |
| `utils.py` | No changes needed |

---

## whisper_client.py (New Module)

HTTP client that calls the Windows Whisper server. Enables Mac to transcribe audio
without local torch/whisper installation.

```python
class WhisperClient:
    def __init__(self, server_url: str, model: str = "large-v3"):
        self.server_url = server_url
        self.model = model

    def health_check(self) -> dict:
        """GET /health - check server status"""

    def transcribe(self, audio_path: Path, language: str = "ko") -> dict:
        """POST /transcribe - send audio file, return transcript"""
        # Returns: {"text": "...", "segments": [...], "srt_result": "..."}
```

---

## Notion DB Design

### New Database: "숨고 클라이언트 회의록"

Location: Under Bridge page (26c50cb0-8d24-80a9-8033-c88460849c53)

| Property | Type | Description |
|----------|------|-------------|
| 제목 | title | Auto: `[클라이언트명] YYYY-MM-DD 미팅` |
| 클라이언트명 | select | Client company name (for tag filtering) |
| 미팅 날짜 | date | Meeting date |
| 미팅 유형 | select | 초기 상담 / 후속 미팅 / 계약 미팅 |
| 담당자 | select | User who uploaded (for telegram routing) |
| 업종 | select | F&B, IT, 제조, 기타 |
| 상태 | select | 진행 중 / 견적 발송 / 계약 완료 / 미진행 |
| AI 요약 | text | One-line summary for list view |

### Views

- **기본 뷰**: 시간순 (최신 먼저)
- **클라이언트별 뷰**: 클라이언트명으로 그룹핑
- **상태별 뷰**: 진행 상태로 필터링

---

## LLM Prompt Design

### Sales Meeting Prompt (영업미팅 특화)

Output structure for Gemini Pro 2.5:

```
## 프로젝트 개요
[고객사 정보 테이블: 고객사명, 업종, 미팅일, 참석자, 미팅 목적]

## 고객 현황 & Pain Points
[고객사가 현재 겪고 있는 문제, 사용 중인 시스템, 불편사항]

## 요구사항 정리
[고객이 요청한 기능/솔루션을 우선순위별로 분류]
- P0 (최우선)
- P1 (높음)
- P2 (보통)

## 제안 가능 솔루션
[미팅에서 논의된 해결 방안, 기술적 접근 방식]

## 견적 & 비즈니스
[비용 관련 논의, 계약 조건, 일정, 예산 범위]

## 후속 액션
### 브릿지 팀
- [ ] 할 일 목록
### 고객사
- [ ] 할 일 목록
### 다음 미팅
- 예정일/주제
```

### Key Prompt Instructions

- Write in Korean (professional tone)
- If manual notes provided, treat as authoritative source
- Extract client company name and industry from conversation
- Prioritize requirements by urgency mentioned in conversation
- Distinguish what was promised vs what needs further review
- Flag any commitments made that need technical validation

---

## Soomgo Minutes UI (pages/2_soomgo_minutes.py)

### Input Section

```
[File Upload: m4a/mp3/wav/txt]
[Client Name: text input or select from existing]
[Meeting Type: 초기 상담 / 후속 미팅 / 계약 미팅]
[Industry: F&B / IT / 제조 / 기타]
[User: 나 / 팀원 (select)]
[Manual Notes: text area (optional)]
[Generate Button]
```

### Processing Flow

1. Upload audio file
2. Call Whisper HTTP server → get transcript
3. Save transcript to file (backup)
4. Call Gemini with sales meeting prompt + manual notes
5. Create Notion page in Soomgo DB with properties + content
6. Send Telegram notification to uploader
7. Show completion with Notion link

### Result Section

- Notion URL link
- Telegram notification status

---

## Telegram Notification

### Multi-user Support

```python
# .env
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID_USER1=123456    # 나
TELEGRAM_CHAT_ID_USER2=789012    # 팀원

# config.py
TELEGRAM_USERS = {
    "나": os.getenv("TELEGRAM_CHAT_ID_USER1"),
    "팀원": os.getenv("TELEGRAM_CHAT_ID_USER2"),
}
```

### Notification Content

```
📋 숨고 클라이언트 회의록 생성 완료

클라이언트: {client_name}
미팅 유형: {meeting_type}
담당자: {user_name}

📎 노션에서 보기: {notion_url}
```

---

## Environment Variables (New)

```bash
# Whisper HTTP Server
WHISPER_SERVER_URL=http://100.71.112.103:8765

# Soomgo Notion DB
SOOMGO_NOTION_DB_ID=<to be created>

# Telegram per-user
TELEGRAM_CHAT_ID_USER1=<chat_id>
TELEGRAM_CHAT_ID_USER2=<chat_id>
```

---

## Implementation Plan

### Phase 1: Infrastructure (Small)

- [ ] Create `whisper_client.py` (HTTP client for Whisper server)
- [ ] Create `.env` on Mac with all required keys
- [ ] Test Whisper HTTP client with sample audio
- [ ] Create Notion "숨고 클라이언트 회의록" database under Bridge

### Phase 2: Streamlit Multipage (Medium)

- [ ] Convert `app.py` to multipage router
- [ ] Move existing logic to `pages/1_bridge_minutes.py`
- [ ] Create `pages/2_soomgo_minutes.py` with UI
- [ ] Test Bridge page still works after migration

### Phase 3: Soomgo Pipeline (Medium)

- [ ] Add sales meeting prompt to `llm_processor.py`
- [ ] Add Soomgo DB methods to `notion_integration.py`
- [ ] Integrate: upload → whisper → gemini → notion flow
- [ ] Test end-to-end with real audio file

### Phase 4: Notifications & Hosting (Small)

- [ ] Add per-user telegram routing to `telegram_notify.py`
- [ ] Setup Cloudflare Tunnel on Mac
- [ ] Share URL with teammate
- [ ] Test teammate access

---

## TODO List Summary

| Phase | File | Change | Verification |
|-------|------|--------|-------------|
| 1 | `whisper_client.py` | New: HTTP client | `pytest` + manual test with m4a |
| 1 | `.env` | New: Mac environment | Config.validate() passes |
| 1 | Notion | New DB creation | DB visible in Bridge page |
| 2 | `app.py` | Simplify to router | App loads without errors |
| 2 | `pages/1_bridge_minutes.py` | Move existing logic | Existing flow still works |
| 2 | `pages/2_soomgo_minutes.py` | New: Soomgo UI | Page renders correctly |
| 3 | `llm_processor.py` | Add sales prompt | Output matches expected structure |
| 3 | `notion_integration.py` | Add Soomgo DB methods | Page created in correct DB |
| 3 | Integration | End-to-end test | Audio → Notion page complete |
| 4 | `telegram_notify.py` | Per-user routing | Correct user gets notification |
| 4 | `config.py` | Add Soomgo config | All new env vars loaded |
| 4 | Cloudflare Tunnel | Setup + test | Teammate can access via URL |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Whisper server offline | Transcription fails | Health check before processing, show clear error |
| Mac not running | Teammate can't access | Consider adding "server status" indicator |
| Large audio files | Slow upload to Whisper | Show progress, max 500MB (existing limit) |
| Gemini API quota | LLM processing fails | Error handling with retry |
