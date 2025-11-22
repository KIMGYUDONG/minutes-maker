import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if torch is available (for conditional test skipping)
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

@pytest.fixture
def has_torch():
    """Fixture to check if torch is available."""
    return HAS_TORCH

@pytest.fixture
def mock_whisper(mocker):
    """
    Mocks the Whisper model to avoid GPU usage and large downloads.
    Returns a mock model that produces 'Hello World' transcription.
    """
    mock_model = MagicMock()
    # Mock the transcribe method to return a fixed result
    mock_model.transcribe.return_value = {
        "text": "Hello World",
        "segments": [],
        "language": "en"
    }
    
    # Patch whisper.load_model to return our mock model
    # We use 'audio_processor.whisper.load_model' if it's imported there, 
    # or 'whisper.load_model' globally. 
    # Safest is to patch where it is used.
    mocker.patch("whisper.load_model", return_value=mock_model)
    
    return mock_model

@pytest.fixture
def mock_gemini(mocker):
    """
    Mocks the Gemini Pro API to avoid network calls and costs.
    Returns a valid markdown response with required headers.
    """
    mock_response = MagicMock()
    mock_response.text = """## 📝 Summary
This is a mock summary for testing purposes.

## 🔑 Key Updates
- Mock update 1
- Mock update 2

## 💬 Discussion Log
- User: Hello
- AI: World

## ✅ Action Items
- [ ] Mock task 1
- [ ] Mock task 2"""
    
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    
    # Patch the GenerativeModel constructor
    mocker.patch("google.generativeai.GenerativeModel", return_value=mock_model)
    
    return mock_model

@pytest.fixture
def mock_notion(mocker):
    """
    Mocks the Notion Client to avoid API calls.
    """
    mock_client = MagicMock()

    # Mock the pages.create method
    mock_client.pages.create.return_value = {"id": "mock_page_id"}

    # Patch the Notion Client
    mocker.patch("notion_integration.Client", return_value=mock_client)

    return mock_client


# ============================================================================
# BEHAVIOR TESTING FIXTURES (Real API, no mocks)
# ============================================================================

@pytest.fixture
def real_notion_client():
    """Real NotionClient for behavior testing.

    Uses actual Notion API - no mocking.
    Tests using this fixture will create real pages.
    """
    from notion_integration import NotionClient
    return NotionClient()


@pytest.fixture
def real_llm_processor():
    """Real LLMProcessor for behavior testing.

    Uses actual Gemini API - no mocking.
    Tests using this fixture will make real API calls.
    """
    from llm_processor import LLMProcessor
    return LLMProcessor()


@pytest.fixture
def test_meeting_data():
    """Sample meeting data for behavior tests."""
    from tests.helpers.notion_helper import SAMPLE_MEETING_DATA
    return SAMPLE_MEETING_DATA.copy()


@pytest.fixture
def test_transcript():
    """Sample transcript for behavior tests."""
    from tests.helpers.gemini_helper import SAMPLE_TEST_TRANSCRIPT
    return SAMPLE_TEST_TRANSCRIPT


@pytest.fixture
def test_manual_notes():
    """Sample manual notes for behavior tests."""
    from tests.helpers.gemini_helper import SAMPLE_TEST_MANUAL_NOTES
    return SAMPLE_TEST_MANUAL_NOTES


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_pages():
    """Automatically clean up test Notion pages at end of session."""
    yield  # Run tests

    # Cleanup after all tests
    from tests.helpers.notion_helper import cleanup_all_test_pages
    cleanup_all_test_pages()
