"""Notion API helpers for behavior testing.

Provides utilities to work with real Notion API in tests:
- Create test pages
- Fetch and verify page content
- Clean up test pages after tests
"""

from typing import Dict, List, Optional
from notion_client import Client
from config import Config
import time


# Track created test pages for cleanup
_test_pages_created = []


def create_test_notion_page(
    title: str,
    content: Dict[str, str],
    icon: str = "📝"
) -> str:
    """Create a real Notion page for testing.

    Args:
        title: Page title
        content: Dictionary with sections (summary, key_updates, etc.)
        icon: Page icon emoji

    Returns:
        str: Notion page URL

    Note:
        Pages are tracked and will be cleaned up after test session.
    """
    from notion_integration import NotionClient

    client = NotionClient()
    url = client.create_meeting_minutes(
        summary=content.get("summary", ""),
        key_updates=content.get("key_updates", ""),
        discussion_log=content.get("discussion_log", ""),
        action_items=content.get("action_items", "")
    )

    # Track for cleanup
    page_id = extract_page_id_from_url(url)
    _test_pages_created.append(page_id)

    return url


def fetch_notion_page_content(url: str) -> str:
    """Fetch actual content from a Notion page.

    Args:
        url: Notion page URL

    Returns:
        str: Page content as text

    Note:
        This makes a real API call to Notion.
    """
    client = Client(auth=Config.NOTION_TOKEN)
    page_id = extract_page_id_from_url(url)

    # Get page blocks
    blocks = client.blocks.children.list(block_id=page_id)

    # Extract text content from blocks
    content_parts = []
    for block in blocks.get("results", []):
        block_type = block.get("type")

        if block_type == "heading_1":
            text = _extract_text_from_rich_text(block["heading_1"]["rich_text"])
            content_parts.append(f"# {text}")

        elif block_type == "heading_2":
            text = _extract_text_from_rich_text(block["heading_2"]["rich_text"])
            content_parts.append(f"## {text}")

        elif block_type == "paragraph":
            text = _extract_text_from_rich_text(block["paragraph"]["rich_text"])
            if text:
                content_parts.append(text)

        elif block_type == "bulleted_list_item":
            text = _extract_text_from_rich_text(block["bulleted_list_item"]["rich_text"])
            content_parts.append(f"- {text}")

        elif block_type == "to_do":
            text = _extract_text_from_rich_text(block["to_do"]["rich_text"])
            checked = block["to_do"]["checked"]
            checkbox = "[x]" if checked else "[ ]"
            content_parts.append(f"{checkbox} {text}")

        elif block_type == "toggle":
            text = _extract_text_from_rich_text(block["toggle"]["rich_text"])
            content_parts.append(f"▶ {text}")

    return "\n".join(content_parts)


def verify_notion_page_structure(url: str, expected_sections: List[str]) -> bool:
    """Verify that a Notion page contains expected sections.

    Args:
        url: Notion page URL
        expected_sections: List of section names to verify

    Returns:
        bool: True if all sections are present
    """
    content = fetch_notion_page_content(url)

    for section in expected_sections:
        if section not in content:
            return False

    return True


def delete_test_page(url: str) -> None:
    """Delete a test Notion page (archive it).

    Args:
        url: Notion page URL to delete
    """
    client = Client(auth=Config.NOTION_TOKEN)
    page_id = extract_page_id_from_url(url)

    try:
        client.pages.update(page_id=page_id, archived=True)
    except Exception as e:
        # Ignore errors during cleanup
        print(f"Warning: Could not delete test page {page_id}: {e}")


def cleanup_all_test_pages() -> None:
    """Clean up all test pages created during this session."""
    client = Client(auth=Config.NOTION_TOKEN)

    for page_id in _test_pages_created:
        try:
            client.pages.update(page_id=page_id, archived=True)
        except Exception:
            pass  # Ignore errors during cleanup

    _test_pages_created.clear()


def extract_page_id_from_url(url: str) -> str:
    """Extract page ID from Notion URL.

    Args:
        url: Notion page URL (e.g., https://notion.so/Page-Title-abc123...)

    Returns:
        str: Page ID (32-character UUID with dashes)
    """
    # URL format: https://www.notion.so/Page-Title-{32-char-id}
    # Extract last 32 characters (without dashes) and format as UUID

    import re

    # Find 32-character hex string
    match = re.search(r'([a-f0-9]{32})', url)
    if not match:
        raise ValueError(f"Could not extract page ID from URL: {url}")

    page_id_no_dashes = match.group(1)

    # Format as UUID: 8-4-4-4-12
    page_id = (
        f"{page_id_no_dashes[0:8]}-"
        f"{page_id_no_dashes[8:12]}-"
        f"{page_id_no_dashes[12:16]}-"
        f"{page_id_no_dashes[16:20]}-"
        f"{page_id_no_dashes[20:32]}"
    )

    return page_id


def wait_for_notion_api(seconds: float = 0.5) -> None:
    """Wait to respect Notion API rate limits.

    Args:
        seconds: Time to wait in seconds (default: 0.5s = 2 req/s)
    """
    time.sleep(seconds)


def _extract_text_from_rich_text(rich_text: List[Dict]) -> str:
    """Extract plain text from Notion rich_text array.

    Args:
        rich_text: Notion rich_text array

    Returns:
        str: Concatenated plain text
    """
    if not rich_text:
        return ""

    return "".join(item.get("text", {}).get("content", "") for item in rich_text)


def is_garbled_korean(text: str) -> bool:
    """Check if Korean text is garbled (encoding issues).

    Args:
        text: Text to check

    Returns:
        bool: True if text appears to be garbled Korean
    """
    # Check for common garbled patterns
    garbled_patterns = [
        "ê°€",  # 가 in UTF-8 bytes
        "í•œ",  # 한 in UTF-8 bytes
        "ê¸€",  # 글 in UTF-8 bytes
        "\\ud",  # Unicode escape sequences
        "\\x",   # Hex escape sequences
    ]

    return any(pattern in text for pattern in garbled_patterns)


# Sample test data
SAMPLE_MEETING_DATA = {
    "summary": "신규 프로젝트 일정과 리소스 배정에 대한 회의를 진행했습니다.",
    "key_updates": "- 기획안 80% 완료\n- 개발팀 3명 투입 예정\n- 다음 주 월요일 킥오프 미팅",
    "discussion_log": "김과장: 현재 기획안이 80% 완료되었습니다.\n팀장: 개발팀은 언제부터 투입 가능한가요?\n이대리: 다음 달 초부터 가능합니다.",
    "action_items": "- 기획안 최종본 작성 (김과장, ~11/30)\n- 개발팀 투입 일정 확정 (이대리, ~12/1)\n- 킥오프 미팅 일정 잡기 (팀장, ~11/27)"
}
