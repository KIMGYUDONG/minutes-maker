import pytest
from unittest.mock import MagicMock
from llm_processor import LLMProcessor

def test_create_meeting_minutes_mock(mock_gemini):
    """
    Test create_meeting_minutes() using the mocked Gemini model.
    Verify it returns the correct dictionary structure.
    """
    processor = LLMProcessor()
    
    result = processor.create_meeting_minutes("Dummy transcript", "Dummy notes")
    
    assert "summary" in result
    assert "key_updates" in result
    assert "discussion_log" in result
    assert "action_items" in result
    assert "This is a mock summary" in result["summary"]

def test_gemini_404_handling(mock_gemini):
    """
    Test handling of 404 Model Not Found error.
    """
    # Configure mock to raise an exception
    mock_gemini.generate_content.side_effect = Exception("404 Model Not Found")
    
    processor = LLMProcessor()
    
    with pytest.raises(RuntimeError) as excinfo:
        processor.create_meeting_minutes("Transcript")
    
    assert "Failed to generate meeting minutes" in str(excinfo.value)
    assert "404 Model Not Found" in str(excinfo.value)
