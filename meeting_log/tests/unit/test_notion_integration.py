"""Comprehensive tests for Notion integration module."""

import pytest
from unittest.mock import MagicMock, patch
from notion_integration import NotionClient


class TestNotionClientInitialization:
    """Test NotionClient initialization and configuration validation."""

    def test_init_success(self):
        """Test successful initialization with valid config."""
        with patch('notion_integration.Config') as mock_config, \
             patch('notion_integration.Client') as mock_client:
            mock_config.NOTION_TOKEN = "test_token"
            mock_config.NOTION_PAGE_ID = "test_page_id"

            client = NotionClient()

            assert client.page_id == "test_page_id"
            mock_client.assert_called_once_with(auth="test_token")

    def test_init_missing_token(self):
        """Test initialization fails when NOTION_TOKEN is missing."""
        with patch('notion_integration.Config') as mock_config:
            mock_config.NOTION_TOKEN = None
            mock_config.NOTION_PAGE_ID = "test_page_id"

            with pytest.raises(ValueError, match="NOTION_TOKEN is not configured"):
                NotionClient()

    def test_init_missing_page_id(self):
        """Test initialization fails when NOTION_PAGE_ID is missing."""
        with patch('notion_integration.Config') as mock_config:
            mock_config.NOTION_TOKEN = "test_token"
            mock_config.NOTION_PAGE_ID = None

            with pytest.raises(ValueError, match="NOTION_PAGE_ID is not configured"):
                NotionClient()


class TestHeadingBlock:
    """Test heading block creation."""

    @pytest.fixture
    def client(self, monkeypatch):
        """Create a NotionClient instance for testing."""
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_heading_level_2(self, client):
        """Test creating H2 heading block."""
        block = client._heading_block("요약", level=2)

        assert block["object"] == "block"
        assert block["type"] == "heading_2"
        assert block["heading_2"]["rich_text"][0]["text"]["content"] == "요약"

    def test_heading_level_1(self, client):
        """Test creating H1 heading block."""
        block = client._heading_block("제목", level=1)

        assert block["type"] == "heading_1"
        assert block["heading_1"]["rich_text"][0]["text"]["content"] == "제목"

    def test_heading_korean_text(self, client):
        """Test heading with Korean text."""
        korean_text = "업데이트"
        block = client._heading_block(korean_text, level=2)

        assert block["heading_2"]["rich_text"][0]["text"]["content"] == korean_text


class TestParagraphBlock:
    """Test paragraph block creation."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_paragraph_simple_text(self, client):
        """Test creating paragraph with simple text."""
        blocks = client._paragraph_block("Simple text")

        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Simple text"

    def test_paragraph_korean_text(self, client):
        """Test creating paragraph with Korean text."""
        korean = "이번 회의에서는 다음 사항을 논의했습니다."
        blocks = client._paragraph_block(korean)

        assert len(blocks) == 1
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == korean

    def test_paragraph_chunking_long_text(self, client):
        """Test paragraph chunks text over 2000 characters."""
        long_text = "a" * 2500  # 2500 characters
        blocks = client._paragraph_block(long_text)

        # Should be chunked into multiple blocks
        assert len(blocks) >= 2

        # Verify all blocks are paragraphs
        for block in blocks:
            assert block["type"] == "paragraph"

        # Verify total content length matches (approximately)
        total_length = sum(len(b["paragraph"]["rich_text"][0]["text"]["content"]) for b in blocks)
        assert total_length <= 2500


class TestBulletedListBlock:
    """Test bulleted list block creation."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_bulleted_list_simple(self, client):
        """Test creating bulleted list item."""
        blocks = client._bulleted_list_block("List item")

        assert len(blocks) == 1
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "List item"

    def test_bulleted_list_korean(self, client):
        """Test bulleted list with Korean text."""
        korean = "한글 리스트 아이템"
        blocks = client._bulleted_list_block(korean)

        assert blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == korean

    def test_bulleted_list_chunking(self, client):
        """Test bulleted list chunks long text."""
        long_text = "b" * 2500
        blocks = client._bulleted_list_block(long_text)

        assert len(blocks) >= 2
        for block in blocks:
            assert block["type"] == "bulleted_list_item"


class TestTodoBlock:
    """Test to-do block creation."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_todo_simple(self, client):
        """Test creating to-do block."""
        blocks = client._todo_block("Task to do")

        assert len(blocks) == 1
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "Task to do"
        assert blocks[0]["to_do"]["checked"] is False

    def test_todo_korean(self, client):
        """Test to-do with Korean text."""
        korean = "할 일 항목"
        blocks = client._todo_block(korean)

        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == korean

    def test_todo_unchecked_by_default(self, client):
        """Test to-do blocks are unchecked by default."""
        blocks = client._todo_block("New task")

        assert blocks[0]["to_do"]["checked"] is False


class TestTextToBlocks:
    """Test text to blocks conversion."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_plain_text_to_paragraph(self, client):
        """Test plain text converts to paragraph."""
        text = "Plain paragraph text"
        blocks = client._text_to_blocks(text)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"

    def test_hyphen_list_to_bullets(self, client):
        """Test text starting with '-' converts to bulleted list."""
        text = "- List item"
        blocks = client._text_to_blocks(text)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "List item"

    def test_bullet_symbol_to_bullets(self, client):
        """Test text starting with '•' converts to bulleted list."""
        text = "• Bullet point"
        blocks = client._text_to_blocks(text)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == "Bullet point"

    def test_mixed_text_formats(self, client):
        """Test mixed paragraphs and lists."""
        text = """Regular paragraph
- List item 1
- List item 2
Another paragraph"""

        blocks = client._text_to_blocks(text)

        assert len(blocks) == 4
        assert blocks[0]["type"] == "paragraph"
        assert blocks[1]["type"] == "bulleted_list_item"
        assert blocks[2]["type"] == "bulleted_list_item"
        assert blocks[3]["type"] == "paragraph"

    def test_empty_text_returns_no_content(self, client):
        """Test empty text returns '(No content)' paragraph."""
        blocks = client._text_to_blocks("")

        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "(No content)"

    def test_whitespace_only_returns_no_content(self, client):
        """Test whitespace-only text returns '(No content)'."""
        blocks = client._text_to_blocks("   \n  \n  ")

        assert len(blocks) == 1
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "(No content)"


class TestActionItemsToBlocks:
    """Test action items conversion to to-do blocks."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_simple_action_item(self, client):
        """Test converting simple action item to to-do."""
        text = "Complete the report"
        blocks = client._action_items_to_blocks(text)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "to_do"
        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "Complete the report"

    def test_action_item_strips_hyphen(self, client):
        """Test action item strips leading hyphen."""
        text = "- Write documentation"
        blocks = client._action_items_to_blocks(text)

        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "Write documentation"

    def test_action_item_strips_bullet(self, client):
        """Test action item strips bullet symbol."""
        text = "• Review code"
        blocks = client._action_items_to_blocks(text)

        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "Review code"

    def test_action_item_strips_checkbox_syntax(self, client):
        """Test action item strips checkbox syntax."""
        test_cases = [
            ("[ ] Unchecked task", "Unchecked task"),
            ("[x] Checked task", "Checked task"),
            ("[] Empty checkbox", "Empty checkbox"),
        ]

        for input_text, expected_content in test_cases:
            blocks = client._action_items_to_blocks(input_text)
            assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == expected_content

    def test_multiple_action_items(self, client):
        """Test converting multiple action items."""
        text = """- Task 1
- Task 2
• Task 3"""

        blocks = client._action_items_to_blocks(text)

        assert len(blocks) == 3
        assert all(block["type"] == "to_do" for block in blocks)
        assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "Task 1"
        assert blocks[1]["to_do"]["rich_text"][0]["text"]["content"] == "Task 2"
        assert blocks[2]["to_do"]["rich_text"][0]["text"]["content"] == "Task 3"

    def test_empty_action_items(self, client):
        """Test empty action items returns 'No action items'."""
        blocks = client._action_items_to_blocks("")

        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "No action items"


class TestBuildBlocks:
    """Test complete block building for all sections."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_build_blocks_structure(self, client):
        """Test _build_blocks creates correct structure with all 4 sections."""
        summary = "Meeting summary"
        key_updates = "Update 1"
        discussion = "Discussion point"
        actions = "Action item"

        blocks = client._build_blocks(summary, key_updates, discussion, actions)

        # Should have 4 headings + 4 content blocks minimum
        assert len(blocks) >= 8

        # Check Korean section headers exist
        heading_texts = [
            b["heading_2"]["rich_text"][0]["text"]["content"]
            for b in blocks if b["type"] == "heading_2"
        ]

        assert "요약" in heading_texts
        assert "업데이트" in heading_texts
        assert "논의사항" in heading_texts
        assert "할 일" in heading_texts

    def test_build_blocks_section_order(self, client):
        """Test sections are in correct order."""
        blocks = client._build_blocks("A", "B", "C", "D")

        # Find all heading blocks
        headings = [
            b["heading_2"]["rich_text"][0]["text"]["content"]
            for b in blocks if b["type"] == "heading_2"
        ]

        # Verify order
        assert headings == ["요약", "업데이트", "논의사항", "할 일"]


class TestCreateMeetingMinutes:
    """Test the main create_meeting_minutes method."""

    @pytest.fixture
    def client(self):
        with patch('notion_integration.Config') as mock_config, \
             patch('notion_integration.Client') as mock_client_class:
            mock_config.NOTION_TOKEN = "test_token"
            mock_config.NOTION_PAGE_ID = "test_database_id"

            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            client = NotionClient()
            client.client = mock_instance

            yield client

    def test_create_meeting_minutes_success(self, client):
        """Test successful meeting minutes creation."""
        # Mock the API response
        client.client.pages.create.return_value = {
            "id": "page_123",
            "url": "https://notion.so/page_123"
        }

        url = client.create_meeting_minutes(
            summary="Summary",
            key_updates="Updates",
            discussion_log="Discussion",
            action_items="Actions"
        )

        assert url == "https://notion.so/page_123"
        client.client.pages.create.assert_called_once()

    def test_create_meeting_minutes_title_format(self, client):
        """Test page title has correct Korean format."""
        client.client.pages.create.return_value = {"url": "https://notion.so/test"}

        client.create_meeting_minutes("A", "B", "C", "D")

        call_args = client.client.pages.create.call_args
        properties = call_args[1]["properties"]
        title_content = properties["제목"]["title"][0]["text"]["content"]

        # Should match "팀 주간 회의 YYYY-MM-DD" format
        assert title_content.startswith("팀 주간 회의")
        assert len(title_content.split("-")) == 3  # Date has 2 hyphens

    def test_create_meeting_minutes_page_icon(self, client):
        """Test page has correct emoji icon."""
        client.client.pages.create.return_value = {"url": "https://notion.so/test"}

        client.create_meeting_minutes("A", "B", "C", "D")

        call_args = client.client.pages.create.call_args
        icon = call_args[1]["icon"]

        assert icon["type"] == "emoji"
        assert icon["emoji"] == "🧐"

    def test_create_meeting_minutes_database_parent(self, client):
        """Test page is created under correct database."""
        client.client.pages.create.return_value = {"url": "https://notion.so/test"}

        client.create_meeting_minutes("A", "B", "C", "D")

        call_args = client.client.pages.create.call_args
        parent = call_args[1]["parent"]

        assert parent["database_id"] == "test_database_id"

    def test_create_meeting_minutes_api_error(self, client):
        """Test error handling when API fails."""
        client.client.pages.create.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Failed to create Notion page"):
            client.create_meeting_minutes("A", "B", "C", "D")


class TestKoreanTextHandling:
    """Test Korean text encoding and handling."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "test_token")
        monkeypatch.setenv("NOTION_PAGE_ID", "test_page_id")

        with patch('notion_integration.Client'):
            return NotionClient()

    def test_korean_in_all_block_types(self, client):
        """Test Korean text works in all block types."""
        korean = "한글 텍스트"

        # Test heading
        heading = client._heading_block(korean, level=2)
        assert heading["heading_2"]["rich_text"][0]["text"]["content"] == korean

        # Test paragraph
        para = client._paragraph_block(korean)
        assert para[0]["paragraph"]["rich_text"][0]["text"]["content"] == korean

        # Test bullet list
        bullet = client._bulleted_list_block(korean)
        assert bullet[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] == korean

        # Test to-do
        todo = client._todo_block(korean)
        assert todo[0]["to_do"]["rich_text"][0]["text"]["content"] == korean

    def test_mixed_korean_english(self, client):
        """Test mixed Korean and English text."""
        mixed = "Meeting 회의 Summary 요약"
        blocks = client._paragraph_block(mixed)

        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == mixed
