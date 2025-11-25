# SPEC-003: LLM Integration

**Status**: Implemented
**Version**: 1.0
**Last Updated**: 2025-11-22
**Owner**: Meeting Minutes Team
**Dependencies**: SPEC-001 (Architecture)

---

## Overview

The LLM Integration module (`llm_processor.py`) uses Google Gemini Pro 2.5 to generate structured meeting minutes in Korean from audio transcripts and manual notes.

## Requirements

### Functional Requirements

**FR-001**: Generate meeting minutes from transcript and optional manual notes
**FR-002**: Output must be in Korean language
**FR-003**: Structure output into 4 sections (요약, 업데이트, 논의사항, 할 일)
**FR-004**: Prioritize manual notes as authoritative source when provided
**FR-005**: Use hierarchical numbering format (1. → a. → •)
**FR-006**: Parse LLM response into structured sections

### Non-Functional Requirements

**NFR-001**: Generate minutes within 30 seconds
**NFR-002**: Handle API errors gracefully
**NFR-003**: Produce consistent output format
**NFR-004**: Support transcripts up to 50,000 characters

## Architecture

### Class: LLMProcessor

```python
class LLMProcessor:
    """Handles meeting minutes generation using Gemini Pro."""

    def __init__(self)
    def create_meeting_minutes(
        self,
        transcript: str,
        manual_notes: Optional[str] = None
    ) -> dict

    # Private methods
    def _build_prompt(self, transcript: str, manual_notes: Optional[str]) -> str
    def _parse_response(self, response_text: str) -> dict
```

### Component Diagram

```
LLMProcessor
├── Initialization
│   ├── Load Gemini API Key
│   ├── Configure genai library
│   └── Create GenerativeModel instance
│
├── Prompt Building
│   ├── Input: Transcript + Manual Notes
│   ├── Template: Korean instructions
│   ├── Format: Hierarchical structure spec
│   └── Output: Formatted prompt
│
├── LLM Generation
│   ├── Model: gemini-2.5-pro
│   ├── Parameters: temperature, top_p, max_tokens
│   ├── API Call: generate_content()
│   └── Output: Raw markdown text
│
└── Response Parsing
    ├── Section Detection: Korean headers
    ├── Content Extraction: Line-by-line parsing
    ├── Validation: Ensure all sections present
    └── Output: Structured dict (4 sections + raw)
```

## Detailed Specifications

### 1. Initialization

**Purpose**: Set up Gemini Pro client with API key

```python
def __init__(self):
    """Initialize the Gemini Pro client."""
    if not Config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    genai.configure(api_key=Config.GEMINI_API_KEY)
    self.model = genai.GenerativeModel(Config.GEMINI_MODEL_NAME)
```

**Configuration**:
- **Model**: gemini-2.5-pro (from config.py)
- **API Key**: Loaded from environment variable
- **Validation**: Raises error if key missing

**Error Handling**:
```python
# Missing API key
ValueError: "GEMINI_API_KEY is not configured"
```

### 2. Meeting Minutes Generation

**Purpose**: Generate structured minutes from transcript and notes

**Implementation**: `create_meeting_minutes(transcript, manual_notes) -> dict`

**Parameters**:
```python
transcript: str          # Required, from Whisper
manual_notes: str | None # Optional, from user input
```

**Process**:
1. Build prompt with transcript and manual notes
2. Call Gemini API with generation config
3. Parse response into structured sections
4. Return dictionary with 4 sections + raw output

**Generation Configuration**:
```python
generation_config = genai.types.GenerationConfig(
    temperature=0.3,      # Lower = more focused output
    top_p=0.8,            # Nucleus sampling
    top_k=40,             # Top-k sampling
    max_output_tokens=2048  # Maximum response length
)
```

**Why These Parameters?**
- **temperature=0.3**: Ensures consistent, professional output (not creative)
- **top_p=0.8**: Balances quality and diversity
- **max_output_tokens=2048**: Accommodates detailed meeting minutes

### 3. Prompt Building

**Purpose**: Construct detailed Korean prompt for Gemini Pro

**Implementation**: `_build_prompt(transcript, manual_notes) -> str`

**Prompt Structure**:

```
┌─────────────────────────────────────┐
│ System Instructions (Korean)        │
│ - Role: Meeting minutes assistant   │
│ - Language: Korean                  │
│ - Format: Hierarchical (1.→a.→•)    │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│ Output Format Specification         │
│ - Section 1: 요약 (Summary)         │
│ - Section 2: 업데이트 (Updates)     │
│ - Section 3: 논의사항 (Discussion)  │
│ - Section 4: 할 일 (Action Items)   │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│ Hierarchical Structure Rules        │
│ - Main points: 1., 2., 3.           │
│ - Sub-points: a., b., c.            │
│ - Details: •                        │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│ Input Data                          │
│ - Audio Transcript (from Whisper)   │
│ - Manual Notes (from user, optional)│
└─────────────────────────────────────┘
```

**Full Prompt Template**:

```markdown
You are an expert meeting minutes assistant for a Korean team. Your task is to create comprehensive, well-structured meeting minutes in Korean.

You will receive:
1. **Audio Transcript**: Automatically transcribed speech from the meeting
2. **Manual Notes**: Hand-written notes provided by the user (may be empty)

**IMPORTANT INSTRUCTIONS:**
- If manual notes are provided, treat them as the AUTHORITATIVE source
- Use the transcript to enrich details and provide context
- If there's a conflict, prioritize the manual notes
- Merge both sources intelligently to create comprehensive minutes
- Write in clear, professional Korean
- Focus on actionable insights and decisions
- Use the hierarchical numbering format: 1. → a. → •

**OUTPUT FORMAT:**
Structure your response EXACTLY as follows with Korean section headers:

## 요약
[2-3 문장으로 회의 전체 내용을 간단히 요약]

## 업데이트
[중요한 업데이트, 결정사항, 공지사항을 계층적으로 구조화]
1. **주요 업데이트 제목**
    a. 세부 사항 1
        • 상세 내용 또는 설명
        • 추가 정보
    b. 세부 사항 2
        • 상세 내용
2. **두 번째 업데이트**
    a. 세부 사항
        • 내용

## 논의사항
[회의에서 논의된 주요 주제와 의견을 구조화]
1. **논의 주제 1**
    a. 참석자 의견 또는 관점
        • 구체적인 논점
        • 추가 논의 내용
    b. 결론 또는 합의사항
2. **논의 주제 2**
    • 주요 논점

## 할 일
[담당자별 액션 아이템을 명확하게 기술]
1. **담당자 이름:**
    • 구체적인 할 일 1
    • 구체적인 할 일 2
2. **다른 담당자:**
    • 할 일

**STRUCTURE RULES:**
- Use "1.", "2.", "3." for main points
- Use "a.", "b.", "c." for sub-points (indented under numbers)
- Use "•" for detailed items (indented under letters)
- Keep formatting consistent throughout

---

**AUDIO TRANSCRIPT:**
```
{transcript}
```

**MANUAL NOTES:**
```
{manual_notes}
```

Now generate the meeting minutes following the exact format above:
```

**Variable Substitution**:
```python
return prompt.format(
    transcript=transcript if transcript else "No transcript available",
    manual_notes=manual_notes if manual_notes else "No manual notes provided"
)
```

### 4. Response Parsing

**Purpose**: Extract structured sections from LLM's markdown output

**Implementation**: `_parse_response(response_text: str) -> dict`

**Output Format**:
```python
{
    "summary": "회의 요약 내용...",
    "key_updates": "1. **업데이트 1**\n    a. 세부사항...",
    "discussion_log": "1. **논의 주제**\n    a. 의견...",
    "action_items": "1. **담당자:**\n    • 할 일...",
    "raw_output": "전체 원본 텍스트..."
}
```

**Parsing Logic**:

**1. Section Detection**
```python
# Korean section headers
if '요약' in line or 'summary' in line_lower:
    if line.startswith('#'):
        current_section = "summary"

if '업데이트' in line or 'updates' in line_lower or 'key updates' in line_lower:
    if line.startswith('#'):
        current_section = "key_updates"

if '논의사항' in line or 'discussion' in line_lower:
    if line.startswith('#'):
        current_section = "discussion_log"

if '할 일' in line or '할일' in line or 'action' in line_lower:
    if line.startswith('#'):
        current_section = "action_items"
```

**2. Content Extraction**
- Split response by lines
- Track current section
- Accumulate lines under each section
- Skip section headers (lines starting with `##`)

**3. Edge Cases**
- **Missing section**: Leave empty string
- **Multiple headers**: Use last occurrence
- **Extra sections**: Ignore (only extract 4 defined sections)

**Example Parsing**:

**Input** (LLM response):
```markdown
## 요약
이번 주간 회의에서는 신규 기능 개발 현황과 일정을 논의했습니다.

## 업데이트
1. **신규 기능 A 개발 완료**
    a. 테스트 완료
        • 단위 테스트 100% 통과

## 논의사항
1. **배포 일정**
    a. 다음 주 목요일 배포 예정

## 할 일
1. **김개발:**
    • 배포 스크립트 작성
```

**Output** (parsed dict):
```python
{
    "summary": "이번 주간 회의에서는 신규 기능 개발 현황과 일정을 논의했습니다.",
    "key_updates": "1. **신규 기능 A 개발 완료**\n    a. 테스트 완료\n        • 단위 테스트 100% 통과",
    "discussion_log": "1. **배포 일정**\n    a. 다음 주 목요일 배포 예정",
    "action_items": "1. **김개발:**\n    • 배포 스크립트 작성",
    "raw_output": "## 요약\n이번 주간 회의에서는..."
}
```

### 5. Error Handling

**API Errors**:
```python
try:
    response = self.model.generate_content(prompt, generation_config)
    result = self._parse_response(response.text)
    return result
except Exception as e:
    raise RuntimeError(f"Failed to generate meeting minutes: {str(e)}")
```

**Common Errors**:

| Error Type | Cause | Recovery |
|------------|-------|----------|
| `400 Bad Request` | Invalid prompt or parameters | Check prompt length |
| `403 Forbidden` | Invalid API key | Verify GEMINI_API_KEY |
| `404 Not Found` | Model doesn't exist | Check GEMINI_MODEL_NAME |
| `429 Too Many Requests` | Rate limit exceeded | Retry after delay |
| `500 Internal Server Error` | Gemini service issue | Retry or wait |

### 6. Multi-Part Response Handling

**Issue**: Gemini API Response Structure Varies by Content Length

**Problem**:
- **Simple Response** (short content): `response.text` works directly
- **Multi-Part Response** (long content): `response.text` raises `ValueError`
- Long transcripts (10,000+ chars) trigger multi-part responses
- Current code (line 48) only handles simple responses

**Root Cause**:
```python
# Current implementation (llm_processor.py:48)
result = self._parse_response(response.text)  # ❌ Fails for multi-part
```

**When Multi-Part Occurs**:
- Input transcript > 10,000 characters
- Output expected to be very long
- Complex structured responses
- Example: 80-minute audio → 20,000+ char transcript → Multi-Part Response

**Error Message**:
```
ValueError: The `response.text` quick accessor only works for simple (single-`Part`)
text responses. This response is not simple text. Use the `result.parts` accessor or
the full `result.candidates[index].content.parts` lookup instead.
```

**Solution**:
```python
# Updated implementation (handles both types)
try:
    response_text = response.text  # Try simple accessor first
except ValueError:
    # Multi-part response: concatenate all parts
    response_text = "".join(part.text for part in response.parts)

result = self._parse_response(response_text)
```

**Test Cases**:
1. **Short transcript** (< 1,000 chars) → Simple Response → ✅ Works
2. **Medium transcript** (3,000 chars) → Simple Response → ✅ Works
3. **Long transcript** (10,000 chars) → May trigger Multi-Part → ✅ Must work
4. **Very long transcript** (20,000+ chars) → Multi-Part Response → ✅ Must work

**Acceptance Criteria**:
- [ ] Handles simple responses (existing behavior)
- [ ] Handles multi-part responses (new behavior)
- [ ] All 37 existing behavior tests pass
- [ ] New test: `test_handles_very_long_transcript()` passes
- [ ] No regression in performance or output quality

### 7. Output Token Limit Handling

**Issue**: Response Truncated for Long Meetings

**Problem**:
- **Current Setting**: `max_output_tokens=2048`
- **Effect**: For 60+ minute meetings, response is cut mid-generation
- **Symptom**: "업데이트" section ends with incomplete text like "3. **"
- **Result**: "논의사항" and "할 일" sections are empty

**Evidence** (80-minute meeting):
```
## 요약
[완료]

## 업데이트
1. 로고 및 앱 아이콘 디자인 최종 확정
2. 오프라인 모임 피드백 공유
3. **           ← 여기서 잘림!

## 논의사항
(No content)    ← 생성되지 않음

## 할 일
No action items ← 생성되지 않음
```

**Root Cause**:
- 2048 tokens ≈ ~1,500-2,000 Korean characters
- 80-minute meeting requires 4,000+ characters output
- Gemini stops generating when limit reached

**Solution**:
```python
# config.py
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "8192"))

# llm_processor.py
from config import GEMINI_MAX_OUTPUT_TOKENS

max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,  # 환경변수 사용
```

**Token Limit Guidelines**:
| 회의 길이 | 권장 토큰 | 환경변수 값 |
|----------|----------|------------|
| < 30분 | 2048 | 2048 |
| 30-60분 | 4096 | 4096 |
| 60분+ | 8192 | 8192 (기본값) |

**Acceptance Criteria**:
- [ ] 환경변수 `GEMINI_MAX_OUTPUT_TOKENS` 지원
- [ ] 기본값 8192 (60분+ 회의 지원)
- [ ] 80분 회의에서 4개 섹션 모두 생성
- [ ] 테스트: `test_handles_long_meeting_output()` 통과

## Dependencies

### Python Packages
```
google-generativeai>=0.3.0   # Gemini SDK
```

### External Services
- **Google Gemini API**: Requires API key from Google AI Studio
- **Internet Connection**: Required for API calls

### Configuration
```bash
# .env file
GEMINI_API_KEY=<your_api_key_here>
GEMINI_MODEL_NAME=gemini-2.5-pro
```

## Testing Strategy

### Unit Tests (`tests/test_llm_processor.py`)
```python
def test_prompt_building():
    """Test prompt construction with transcript and notes"""

def test_response_parsing():
    """Test parsing of Korean section headers"""

def test_missing_sections():
    """Test handling of incomplete LLM responses"""

def test_error_handling():
    """Test API error handling (404, 403, etc.)"""
```

### Integration Tests (`test_llm_only.py`)
```python
def test_real_llm_generation():
    """Test actual Gemini API call with sample data"""
```

### Test Data
```python
SAMPLE_TRANSCRIPT = """
회의를 시작하겠습니다. 이번 주 진행 상황을 공유해 주세요.
김개발: 신규 기능 개발이 완료되었습니다...
"""

SAMPLE_NOTES = """
- 신규 기능 A 개발 완료 (김개발)
- 배포 일정: 다음 주 목요일
- 할 일: 테스트 및 문서화
"""
```

## Performance Metrics

### Response Time
- **Average**: 10-15 seconds
- **Max**: 30 seconds
- **Factors**: Prompt length, model load, API latency

### Token Usage
- **Input tokens**: ~1,500-5,000 (depends on transcript length)
- **Output tokens**: ~500-1,500 (structured minutes)
- **Cost**: ~$0.01-0.05 per request (Gemini Pro pricing)

### Quality Metrics
- **Section accuracy**: 95%+ (all 4 sections present)
- **Korean quality**: Native-level fluency
- **Structure adherence**: 90%+ (correct hierarchical format)

## Configuration

### Generation Parameters

```python
# Lower temperature = more consistent output
temperature = 0.3  # Range: 0.0 (deterministic) to 1.0 (creative)

# Nucleus sampling
top_p = 0.8  # Consider tokens with cumulative probability up to 80%

# Top-k sampling
top_k = 40  # Consider top 40 most probable tokens

# Maximum output length
max_output_tokens = 2048  # Sufficient for detailed minutes
```

### Prompt Engineering Tips
1. **Be specific**: Clearly define output format
2. **Use examples**: Show desired structure
3. **Provide context**: Explain the meeting's purpose
4. **Handle edge cases**: Specify behavior for missing data
5. **Validate output**: Parse and check completeness

## Limitations

### Current Limitations
1. **Korean-only**: Hardcoded for Korean language
2. **Fixed structure**: 4 sections, cannot customize
3. **No validation**: Doesn't verify LLM output quality
4. **No retry**: Single API call, no automatic retry on failure
5. **Token limit**: 2048 tokens may be insufficient for very long meetings

### Workarounds
- **Long meetings**: Split transcript into chunks
- **Poor quality**: Provide more detailed manual notes
- **Wrong language**: Emphasize Korean in manual notes
- **Missing sections**: Use raw_output as fallback

## Future Enhancements

### Potential Improvements
1. **Multi-language support**: Detect and adapt to meeting language
2. **Custom sections**: Allow user-defined section templates
3. **Streaming output**: Show real-time generation progress
4. **Output validation**: Check and request regeneration if incomplete
5. **Retry logic**: Automatic retry with exponential backoff
6. **Quality scoring**: Rate and suggest improvements to output
7. **Conversation history**: Multi-turn refinement of minutes
8. **Sentiment analysis**: Detect and highlight emotional moments

### Technical Debt
- **Hardcoded Korean**: Should support multiple languages
- **No caching**: Same transcript generates new API call each time
- **Prompt versioning**: No tracking of prompt template changes
- **Error recovery**: Limited error handling and recovery

---

**References**:
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Gemini Prompt Design Best Practices](https://ai.google.dev/docs/prompt_best_practices)
- [google-generativeai Python SDK](https://github.com/google/generative-ai-python)
