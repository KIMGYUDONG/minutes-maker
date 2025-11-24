"""Gemini API helpers for behavior testing.

Provides utilities to work with real Gemini API in tests:
- Rate-limited API calls
- Response verification
- Korean text validation
"""

import time
from typing import Dict, Optional
import google.generativeai as genai
from config import Config


# Rate limiting state
_last_api_call_time = 0
_min_call_interval = 1.0  # seconds between calls


def get_real_gemini_response(
    prompt: str,
    max_wait: int = 30,
    temperature: float = 0.7
) -> str:
    """Get real response from Gemini API with rate limiting.

    Args:
        prompt: Prompt to send to Gemini
        max_wait: Maximum seconds to wait for response
        temperature: Model temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        str: Gemini response text

    Raises:
        TimeoutError: If response takes longer than max_wait
        RuntimeError: If API call fails
    """
    global _last_api_call_time

    # Rate limiting: wait if needed
    elapsed = time.time() - _last_api_call_time
    if elapsed < _min_call_interval:
        time.sleep(_min_call_interval - elapsed)

    # Configure Gemini
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel(Config.GEMINI_MODEL_NAME)

    try:
        start_time = time.time()

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=2048,
            )
        )

        elapsed_time = time.time() - start_time

        if elapsed_time > max_wait:
            raise TimeoutError(f"Gemini API call took {elapsed_time:.1f}s (max: {max_wait}s)")

        _last_api_call_time = time.time()

        return response.text

    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")


def verify_gemini_meeting_minutes_structure(response: str) -> bool:
    """Verify that Gemini response has expected meeting minutes structure.

    Args:
        response: Gemini API response text

    Returns:
        bool: True if structure is valid

    Expected sections (Korean):
        - 요약 or Summary
        - 업데이트 or Key Updates or 주요 내용
        - 논의 or Discussion
        - 할 일 or Action Items or 액션
    """
    # Check for at least 2 of the 4 main sections
    sections_found = 0

    if any(keyword in response for keyword in ["요약", "Summary"]):
        sections_found += 1

    if any(keyword in response for keyword in ["업데이트", "Update", "주요"]):
        sections_found += 1

    if any(keyword in response for keyword in ["논의", "Discussion"]):
        sections_found += 1

    if any(keyword in response for keyword in ["할 일", "Action", "액션"]):
        sections_found += 1

    return sections_found >= 2


def verify_korean_response(response: str) -> bool:
    """Verify that response is in Korean.

    Args:
        response: Text to check

    Returns:
        bool: True if response contains Korean characters
    """
    # Check for Korean characters (Hangul Unicode range)
    korean_chars = sum(1 for char in response if '\uac00' <= char <= '\ud7af')

    # Response should have at least 10 Korean characters
    return korean_chars >= 10


def extract_action_items_from_response(response: str) -> list:
    """Extract action items from Gemini response.

    Args:
        response: Gemini meeting minutes text

    Returns:
        list: Action items found (as strings)
    """
    action_items = []

    # Find action items section
    lines = response.split('\n')
    in_action_section = False

    for line in lines:
        # Check if we entered action items section
        if any(keyword in line for keyword in ["할 일", "Action", "액션"]):
            in_action_section = True
            continue

        # Check if we left action items section (new heading)
        if in_action_section and line.strip().startswith('#'):
            break

        # Extract action items
        if in_action_section:
            stripped = line.strip()
            if stripped and (stripped.startswith('-') or stripped.startswith('•')):
                action_items.append(stripped[1:].strip())

    return action_items


def contains_original_content(response: str, original_text: str, min_overlap: int = 50) -> bool:
    """Verify that response contains content from original text.

    Args:
        response: Generated meeting minutes
        original_text: Original transcript or notes
        min_overlap: Minimum characters that should overlap

    Returns:
        bool: True if sufficient overlap found
    """
    # Extract significant words from original (10+ characters)
    import re

    original_words = set(re.findall(r'\S{10,}', original_text))

    # Count how many significant words appear in response
    overlap_chars = sum(
        len(word) for word in original_words if word in response
    )

    return overlap_chars >= min_overlap


# Sample test prompts
SAMPLE_TEST_TRANSCRIPT = """
안녕하세요. 오늘 회의를 시작하겠습니다.
첫 번째 안건은 신규 프로젝트 일정에 대한 논의입니다.
김과장님, 현재 진행 상황을 공유해주시겠습니까?
네, 현재 기획안이 80% 완료되었고, 다음 주까지 최종안을 마무리할 예정입니다.
좋습니다. 개발팀은 언제부터 투입 가능한가요?
다음 달 초부터 가능합니다. 리소스는 3명 배정 예정입니다.
알겠습니다. 그럼 다음 액션 아이템을 정리하겠습니다.
기획안 최종본 작성, 개발팀 투입 일정 확정, 마일스톤 작성이 필요합니다.
다음 주 월요일까지 킥오프 미팅 일정을 잡도록 하겠습니다.
"""

SAMPLE_TEST_MANUAL_NOTES = """
- 신규 프로젝트 일정 논의
- 기획안 다음 주까지 완료
- 개발팀 3명 투입
- 킥오프 미팅 예정
"""


def generate_long_transcript(target_chars: int) -> str:
    """Generate realistic long Korean transcript for testing.

    Args:
        target_chars: Target character count (approximate)

    Returns:
        str: Generated Korean meeting transcript

    Example:
        >>> transcript = generate_long_transcript(20000)
        >>> len(transcript) >= 18000  # Within 10% of target
        True
    """
    # Base realistic meeting segments
    segments = [
        "안녕하세요. 오늘 주간 회의를 시작하겠습니다.",
        "먼저 지난주 진행사항부터 공유해 주시겠습니까?",
        "네, 신규 기능 개발이 예정대로 진행되고 있습니다.",
        "현재 프론트엔드 작업이 80% 완료되었고, 백엔드는 95% 진행 중입니다.",
        "테스트 케이스 작성은 어떻게 되고 있나요?",
        "단위 테스트는 모두 완료되었고, 통합 테스트를 진행 중입니다.",
        "좋습니다. 다음 주 배포 일정은 유지할 수 있을까요?",
        "네, 현재 진행 속도라면 문제없을 것 같습니다.",
        "그럼 액션 아이템을 정리하겠습니다.",
        "김과장님은 프론트엔드 마무리를 담당해 주시고,",
        "이대리님은 백엔드 최종 리뷰를 부탁드립니다.",
        "박팀장님은 배포 계획서를 작성해 주시기 바랍니다.",
        "다음으로 예산 관련 안건을 논의하겠습니다.",
        "이번 분기 예산 사용 현황을 보고 드리겠습니다.",
        "개발 비용이 예상보다 10% 절감되었습니다.",
        "클라우드 인프라 비용도 최적화를 통해 감소했습니다.",
        "절감된 예산으로 추가 교육 프로그램을 진행하면 어떨까요?",
        "좋은 제안입니다. 팀원들의 역량 강화가 필요한 시점입니다.",
        "그럼 다음 달부터 월 1회 외부 강사 초청 세미나를 진행하도록 하겠습니다.",
        "마지막으로 인력 충원 계획에 대해 말씀드리겠습니다.",
    ]

    result = []
    current_length = 0
    segment_index = 0

    while current_length < target_chars:
        # Add segment
        segment = segments[segment_index % len(segments)]
        result.append(segment)
        current_length += len(segment)
        segment_index += 1

        # Add realistic variations every few segments
        if segment_index % 5 == 0:
            result.append(f"그리고 추가로 말씀드리면, 현재 {segment_index // 5}차 검토가 진행 중입니다.")
            current_length += len(result[-1])

        # Add spacing
        result.append("")
        current_length += 1

    return "\n".join(result)
