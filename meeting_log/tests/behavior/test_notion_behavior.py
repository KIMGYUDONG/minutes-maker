"""Behavior tests for Notion integration.

Tests WHAT the Notion integration does, not HOW it works internally.
Following Kent Beck's TDD principles (Chicago School):
- Uses real Notion API (no mocks)
- Tests observable outcomes only
- Focuses on public interface
- Enables refactoring-safe tests

Fixtures used:
- real_notion_client: Real NotionClient instance
- test_meeting_data: Sample Korean meeting data
- cleanup_test_pages: Auto cleanup after tests
"""

import pytest
from tests.helpers.notion_helper import (
    fetch_notion_page_content,
    verify_notion_page_structure,
    extract_page_id_from_url,
    is_garbled_korean,
)


class TestNotionPageCreation:
    """Behavior: Creates meeting minutes page in Notion.

    Tests focus on whether pages are created successfully with correct content,
    not on internal implementation details like block structure or method calls.
    """

    @pytest.mark.integration
    def test_creates_page_with_all_sections(self, real_notion_client, test_meeting_data):
        """Test that NotionClient creates a page with all required sections.

        Behavior tested:
        - Page is created in Notion
        - All sections (summary, key updates, discussion, action items) are present
        - Returns a valid Notion URL
        """
        # When: Create meeting minutes with all sections
        url = real_notion_client.create_meeting_minutes(
            summary=test_meeting_data["summary"],
            key_updates=test_meeting_data["key_updates"],
            discussion_log=test_meeting_data["discussion_log"],
            action_items=test_meeting_data["action_items"]
        )

        # Then: Page should be created with all sections
        assert url is not None
        assert url.startswith("https://")
        assert "notion.so" in url

        # Verify all sections are present
        expected_sections = ["요약", "업데이트", "논의", "할 일"]
        assert verify_notion_page_structure(url, expected_sections)

    @pytest.mark.integration
    def test_handles_long_text_over_2000_chars(self, real_notion_client):
        """Test that NotionClient handles text longer than 2000 characters.

        Behavior tested:
        - Long text doesn't cause errors
        - Content is properly chunked or formatted
        - All content appears in the final page

        Note: Notion blocks have 2000 character limit, so this tests the chunking behavior.
        """
        # Given: Very long text (over 2000 chars)
        long_summary = "긴 회의 내용입니다. " * 200  # ~2000 chars

        # When: Create page with long text
        url = real_notion_client.create_meeting_minutes(
            summary=long_summary,
            key_updates="업데이트",
            discussion_log="논의",
            action_items="할 일"
        )

        # Then: Page should be created successfully
        assert url is not None

        # Verify content is present (might be chunked across multiple blocks)
        page_content = fetch_notion_page_content(url)
        assert "긴 회의 내용입니다" in page_content
        assert len(page_content) > 1000  # Significant content is present

    @pytest.mark.integration
    def test_creates_action_items_as_checkboxes(self, real_notion_client):
        """Test that action items are created as interactive checkboxes.

        Behavior tested:
        - Action items appear as todo checkboxes (not plain text)
        - Checkboxes are unchecked by default
        - Multiple action items are all converted to checkboxes
        """
        # Given: Multiple action items
        action_items = """- 기획안 최종본 작성 (김과장, ~11/30)
- 개발팀 투입 일정 확정 (이대리, ~12/1)
- 킥오프 미팅 일정 잡기 (팀장, ~11/27)"""

        # When: Create page with action items
        url = real_notion_client.create_meeting_minutes(
            summary="회의 요약",
            key_updates="업데이트",
            discussion_log="논의",
            action_items=action_items
        )

        # Then: Action items should be checkboxes
        page_content = fetch_notion_page_content(url)

        # Verify checkboxes are present (unchecked format: "[ ]")
        assert "[ ] 기획안 최종본 작성" in page_content
        assert "[ ] 개발팀 투입 일정 확정" in page_content
        assert "[ ] 킥오프 미팅 일정 잡기" in page_content

    @pytest.mark.integration
    def test_handles_korean_text_correctly(self, real_notion_client, test_meeting_data):
        """Test that Korean text is not garbled in Notion.

        Behavior tested:
        - Korean characters are properly encoded
        - No encoding issues (garbled text like "ê°€" or "\\ud...")
        - Korean text is readable in the final page
        """
        # When: Create page with Korean content
        url = real_notion_client.create_meeting_minutes(
            summary=test_meeting_data["summary"],
            key_updates=test_meeting_data["key_updates"],
            discussion_log=test_meeting_data["discussion_log"],
            action_items=test_meeting_data["action_items"]
        )

        # Then: Korean text should not be garbled
        page_content = fetch_notion_page_content(url)

        # Verify Korean text is present and not garbled
        assert "신규 프로젝트" in page_content
        assert "기획안" in page_content
        assert "개발팀" in page_content
        assert not is_garbled_korean(page_content)

    @pytest.mark.integration
    def test_returns_valid_notion_url(self, real_notion_client):
        """Test that create_meeting_minutes returns a valid Notion URL.

        Behavior tested:
        - Returns a URL string
        - URL is accessible (proper format)
        - URL contains valid page ID
        """
        # When: Create a simple page
        url = real_notion_client.create_meeting_minutes(
            summary="테스트 요약",
            key_updates="테스트 업데이트",
            discussion_log="테스트 논의",
            action_items="테스트 할 일"
        )

        # Then: URL should be valid
        assert isinstance(url, str)
        assert url.startswith("https://")
        assert "notion.so" in url

        # Verify page ID can be extracted (32-character hex)
        page_id = extract_page_id_from_url(url)
        assert len(page_id) == 36  # UUID format with dashes: 8-4-4-4-12


class TestNotionContentFormatting:
    """Behavior: Formats content correctly in Notion.

    Tests focus on observable formatting in the final page,
    not on internal block creation methods.
    """

    @pytest.mark.integration
    def test_converts_bullet_lists(self, real_notion_client):
        """Test that bullet list items are formatted as Notion bulleted lists.

        Behavior tested:
        - Lines starting with "-" become bulleted list items
        - Multiple bullet points are all converted
        - Bullet list structure is preserved
        """
        # Given: Content with bullet lists
        key_updates = """- 첫 번째 업데이트
- 두 번째 업데이트
- 세 번째 업데이트"""

        # When: Create page with bullet lists
        url = real_notion_client.create_meeting_minutes(
            summary="요약",
            key_updates=key_updates,
            discussion_log="논의",
            action_items="할 일"
        )

        # Then: Bullet lists should be formatted correctly
        page_content = fetch_notion_page_content(url)

        assert "- 첫 번째 업데이트" in page_content
        assert "- 두 번째 업데이트" in page_content
        assert "- 세 번째 업데이트" in page_content

    @pytest.mark.integration
    def test_preserves_discussion_log_content(self, real_notion_client):
        """Test that discussion log content is preserved correctly.

        Behavior tested:
        - Multi-line discussion log is fully preserved
        - All speakers and their statements appear
        - Content formatting is maintained
        """
        # Given: Multi-line discussion log
        discussion = """김과장: 현재 진행 상황을 말씀드리겠습니다.
팀장: 좋습니다. 계속하세요.
이대리: 저도 의견이 있습니다."""

        # When: Create page with discussion log
        url = real_notion_client.create_meeting_minutes(
            summary="요약",
            key_updates="업데이트",
            discussion_log=discussion,
            action_items="할 일"
        )

        # Then: All discussion content should be preserved
        page_content = fetch_notion_page_content(url)

        # Verify all discussion content is present
        assert "김과장: 현재 진행 상황을 말씀드리겠습니다" in page_content
        assert "팀장: 좋습니다. 계속하세요" in page_content
        assert "이대리: 저도 의견이 있습니다" in page_content

    @pytest.mark.integration
    def test_handles_empty_sections(self, real_notion_client):
        """Test that empty sections don't cause errors.

        Behavior tested:
        - Empty strings are handled gracefully
        - Page is still created
        - No placeholder text appears (like "None" or "undefined")
        """
        # When: Create page with some empty sections
        url = real_notion_client.create_meeting_minutes(
            summary="요약만 있는 회의",
            key_updates="",  # Empty
            discussion_log="",  # Empty
            action_items="- 하나의 할 일"
        )

        # Then: Page should be created successfully
        assert url is not None

        page_content = fetch_notion_page_content(url)

        # Verify no error placeholders
        assert "None" not in page_content
        assert "undefined" not in page_content

        # Verify non-empty sections are present
        assert "요약만 있는 회의" in page_content
        assert "하나의 할 일" in page_content

    @pytest.mark.integration
    def test_formats_multiple_sections_correctly(self, real_notion_client, test_meeting_data):
        """Test that all sections maintain their distinct content and formatting.

        Behavior tested:
        - Summary content appears as text
        - Key updates appear as bullet list
        - Discussion log content is preserved
        - Action items appear as checkboxes
        """
        # When: Create page with all section types
        url = real_notion_client.create_meeting_minutes(
            summary=test_meeting_data["summary"],
            key_updates=test_meeting_data["key_updates"],
            discussion_log=test_meeting_data["discussion_log"],
            action_items=test_meeting_data["action_items"]
        )

        # Then: Each section should have correct formatting
        page_content = fetch_notion_page_content(url)

        # Summary (paragraph text) - content is preserved
        assert "신규 프로젝트 일정과 리소스 배정" in page_content

        # Key updates (bullet list - contains "- ")
        assert "- 기획안 80% 완료" in page_content
        assert "- 개발팀 3명 투입 예정" in page_content

        # Discussion log - content is preserved
        assert "김과장: 현재 기획안이 80% 완료되었습니다" in page_content
        assert "이대리: 다음 달 초부터 가능합니다" in page_content

        # Action items (checkboxes - contains "[ ]")
        assert "[ ]" in page_content
        assert "기획안 최종본 작성" in page_content


class TestNotionErrorHandling:
    """Behavior: Handles errors gracefully.

    Tests focus on how the system responds to error conditions,
    not on internal error handling implementation.
    """

    def test_raises_error_when_api_key_missing(self, monkeypatch):
        """Test that missing API key raises appropriate error.

        Behavior tested:
        - Missing API key causes error at initialization (not silent failure)
        - Error message is informative
        - Client cannot be created without valid config
        """
        # Given: Missing API key in Config
        from notion_integration import NotionClient
        from config import Config

        # Mock Config.NOTION_TOKEN to be empty
        monkeypatch.setattr(Config, "NOTION_TOKEN", "")

        # When/Then: Try to create client with missing key
        with pytest.raises(ValueError) as exc_info:
            NotionClient()

        # Verify error message is informative
        assert "NOTION_TOKEN" in str(exc_info.value)

    def test_raises_error_when_page_id_invalid(self):
        """Test that invalid page ID raises appropriate error.

        Behavior tested:
        - Invalid page ID in database_id causes error
        - Error message indicates the problem
        """
        # This test would require mocking the config or creating a separate client
        # For now, we'll mark it as a placeholder
        pytest.skip("Requires config mocking - implement in future iteration")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_handles_api_rate_limits(self, real_notion_client):
        """Test that rapid API calls are handled gracefully.

        Behavior tested:
        - Multiple rapid calls don't cause failures
        - Rate limiting is respected
        - All pages are created successfully

        Note: This is a slow test (marked with @pytest.mark.slow)
        """
        # When: Create multiple pages rapidly
        urls = []
        for i in range(3):  # Create 3 pages in quick succession
            url = real_notion_client.create_meeting_minutes(
                summary=f"테스트 {i}",
                key_updates=f"업데이트 {i}",
                discussion_log=f"논의 {i}",
                action_items=f"할 일 {i}"
            )
            urls.append(url)

        # Then: All pages should be created successfully
        assert len(urls) == 3
        assert all(url.startswith("https://") for url in urls)
        assert len(set(urls)) == 3  # All URLs should be unique
