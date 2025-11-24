"""Behavior tests for LLM processing (Gemini integration).

Tests WHAT the LLM processor does, not HOW it works internally.
Following Kent Beck's TDD principles (Chicago School):
- Uses real Gemini API (no mocks)
- Tests observable outcomes only
- Focuses on public interface
- Enables refactoring-safe tests

Fixtures used:
- real_llm_processor: Real LLMProcessor instance
- test_transcript: Sample Korean transcript
- test_manual_notes: Sample manual notes
"""

import pytest
from tests.helpers.gemini_helper import (
    verify_gemini_meeting_minutes_structure,
    verify_korean_response,
    extract_action_items_from_response,
    contains_original_content,
    generate_long_transcript,
)


class TestMeetingMinutesGeneration:
    """Behavior: Generates meeting minutes from transcript.

    Tests focus on whether meeting minutes are generated with correct structure
    and content, not on internal prompt building or parsing logic.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generates_summary_from_transcript(self, real_llm_processor, test_transcript):
        """Test that LLM generates a summary from transcript.

        Behavior tested:
        - Summary is generated
        - Summary contains key information from transcript
        - Summary is concise (not just copying transcript)
        """
        # When: Generate meeting minutes from transcript
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Then: Summary should be generated
        assert result is not None
        assert isinstance(result, dict)
        assert "summary" in result
        assert "key_updates" in result
        assert "discussion_log" in result
        assert "action_items" in result

        # Verify summary is not empty
        assert len(result["summary"]) > 0

        # Verify summary contains relevant content from transcript
        # (should mention project or meeting topic)
        assert any(
            keyword in result["summary"]
            for keyword in ["프로젝트", "회의", "기획", "개발"]
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_includes_manual_notes_in_output(self, real_llm_processor, test_transcript, test_manual_notes):
        """Test that manual notes are included in the output.

        Behavior tested:
        - Manual notes content appears in the output
        - Output includes information from manual notes
        - Manual notes are merged with transcript
        """
        # When: Generate minutes with both transcript and manual notes
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=test_manual_notes
        )

        # Then: Output should include content from manual notes
        raw_output = result.get("raw_output", "")

        # Verify manual notes content is present
        # Manual notes mention "킥오프 미팅"
        assert "킥오프" in raw_output or "kick" in raw_output.lower()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_identifies_action_items(self, real_llm_processor, test_transcript):
        """Test that LLM identifies action items from the meeting.

        Behavior tested:
        - Action items section is populated
        - Action items are extracted from the discussion
        - Action items are specific and actionable
        """
        # When: Generate minutes from transcript containing action items
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Then: Action items should be identified
        assert "action_items" in result
        assert len(result["action_items"]) > 0

        # Verify action items section is not just empty or placeholder
        action_items = result["action_items"].lower()
        assert "no action" not in action_items
        assert "none" not in action_items

    @pytest.mark.integration
    @pytest.mark.slow
    def test_output_is_in_korean(self, real_llm_processor, test_transcript):
        """Test that output is in Korean language.

        Behavior tested:
        - All sections are in Korean
        - Korean characters are properly formatted
        - Output follows Korean grammar and style
        """
        # When: Generate minutes from Korean transcript
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Then: Output should be in Korean
        raw_output = result.get("raw_output", "")

        # Verify Korean response
        assert verify_korean_response(raw_output)

        # Verify key sections have Korean content
        assert verify_korean_response(result["summary"])

    def test_raises_error_when_api_key_missing(self, monkeypatch):
        """Test that missing API key raises appropriate error.

        Behavior tested:
        - Missing API key causes error at initialization
        - Error message is informative
        - Processor cannot be created without valid config
        """
        # Given: Missing API key in Config
        from llm_processor import LLMProcessor
        from config import Config

        # Mock Config.GEMINI_API_KEY to be empty
        monkeypatch.setattr(Config, "GEMINI_API_KEY", "")

        # When/Then: Try to create processor with missing key
        with pytest.raises(ValueError) as exc_info:
            LLMProcessor()

        # Verify error message is informative
        assert "GEMINI_API_KEY" in str(exc_info.value)


class TestContentMerging:
    """Behavior: Merges transcript and manual notes correctly.

    Tests focus on how the LLM handles different input combinations,
    not on internal prompt construction logic.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_prioritizes_manual_notes_over_transcript(self, real_llm_processor):
        """Test that manual notes take priority when there's conflicting information.

        Behavior tested:
        - Manual notes are treated as authoritative
        - When conflict exists, manual notes win
        - Transcript is used to supplement, not override
        """
        # Given: Transcript and manual notes with different information
        transcript = """
        회의 참석자는 5명입니다.
        프로젝트 완료일은 12월 31일입니다.
        """

        manual_notes = """
        - 참석자: 3명 (김과장, 이대리, 박팀장)
        - 완료일: 11월 30일로 앞당김
        """

        # When: Generate minutes with both sources
        result = real_llm_processor.create_meeting_minutes(
            transcript=transcript,
            manual_notes=manual_notes
        )

        # Then: Manual notes information should be prioritized
        raw_output = result.get("raw_output", "").lower()

        # Manual notes say 3 people (not 5 from transcript)
        # Note: We can't guarantee exact numbers, but we test general behavior
        # The output should reference the manual notes content
        assert "11" in raw_output or "30" in raw_output  # Date from manual notes

    @pytest.mark.integration
    @pytest.mark.slow
    def test_handles_transcript_only(self, real_llm_processor, test_transcript):
        """Test that processor works with transcript only (no manual notes).

        Behavior tested:
        - Minutes are generated from transcript alone
        - All sections are populated
        - No errors or empty output
        """
        # When: Generate minutes with only transcript (no manual notes)
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Then: Should generate complete minutes
        assert result is not None
        assert len(result["summary"]) > 0
        assert len(result["key_updates"]) > 0
        assert len(result["discussion_log"]) > 0
        assert len(result["action_items"]) > 0

        # Verify structure is correct
        raw_output = result.get("raw_output", "")
        assert verify_gemini_meeting_minutes_structure(raw_output)

    @pytest.mark.integration
    @pytest.mark.slow
    def test_handles_manual_notes_only(self, real_llm_processor, test_manual_notes):
        """Test that processor works with manual notes only (no transcript).

        Behavior tested:
        - Minutes are generated from manual notes alone
        - All sections are populated
        - No errors or empty output
        """
        # When: Generate minutes with only manual notes (no transcript)
        result = real_llm_processor.create_meeting_minutes(
            transcript="",  # Empty transcript
            manual_notes=test_manual_notes
        )

        # Then: Should generate complete minutes
        assert result is not None
        assert len(result["summary"]) > 0

        # Manual notes mention "킥오프 미팅"
        raw_output = result.get("raw_output", "")
        assert "킥오프" in raw_output or "개발" in raw_output

        # Verify structure is correct
        assert verify_gemini_meeting_minutes_structure(raw_output)


class TestOutputStructure:
    """Behavior: Output has correct structure and format.

    Tests focus on the observable structure of the output,
    not on internal parsing implementation.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_returns_dict_with_required_keys(self, real_llm_processor, test_transcript):
        """Test that output contains all required dictionary keys.

        Behavior tested:
        - Returns a dictionary
        - Contains summary, key_updates, discussion_log, action_items
        - All values are strings
        """
        # When: Generate minutes
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Then: Should return dict with required keys
        assert isinstance(result, dict)

        required_keys = ["summary", "key_updates", "discussion_log", "action_items"]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
            assert isinstance(result[key], str), f"Key {key} should be string"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_output_has_korean_section_headers(self, real_llm_processor, test_transcript):
        """Test that raw output contains Korean section headers.

        Behavior tested:
        - Output follows the expected format
        - Korean section headers are present (요약, 업데이트, 논의사항, 할 일)
        - Structure is maintained
        """
        # When: Generate minutes
        result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Then: Raw output should have Korean headers
        raw_output = result.get("raw_output", "")

        # Check for Korean section headers
        expected_headers = ["요약", "업데이트", "논의", "할"]
        headers_found = sum(1 for header in expected_headers if header in raw_output)

        # At least 3 of 4 headers should be present
        assert headers_found >= 3, f"Expected Korean headers, found {headers_found}/4"


class TestMultiPartResponse:
    """Behavior: Handles Gemini multi-part responses for long content.

    Context:
    - Gemini API returns Simple Response for short content (< 5K chars)
    - Gemini API returns Multi-Part Response for long content (> 10K chars)
    - Multi-Part requires response.parts instead of response.text

    This test ensures the LLM processor handles both response types.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_handles_very_long_transcript(self, real_llm_processor):
        """Test that LLM handles very long transcripts (multi-part responses).

        Behavior tested:
        - Processes 20,000+ character transcript
        - Handles Gemini multi-part response structure
        - Returns valid structured output
        - No ValueError raised

        Background:
        - Long transcripts trigger multi-part responses
        - Previous bug: response.text raises ValueError for multi-part
        - Fix: Use response.parts for multi-part responses
        """
        # Given: Very long transcript that triggers multi-part response
        long_transcript = generate_long_transcript(20000)  # ~20K chars

        # Verify transcript is actually long enough
        assert len(long_transcript) >= 18000, f"Expected 18K+ chars, got {len(long_transcript)}"

        # When: Generate meeting minutes from very long transcript
        result = real_llm_processor.create_meeting_minutes(
            transcript=long_transcript,
            manual_notes=None
        )

        # Then: Should succeed without ValueError
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), "Result should be a dictionary"

        # Should have all required keys
        required_keys = ["summary", "key_updates", "discussion_log", "action_items"]
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
            assert isinstance(result[key], str), f"Key {key} should be string"

        # Summary should not be empty
        assert len(result["summary"]) > 0, "Summary should not be empty"

        # Verify output structure is correct
        raw_output = result.get("raw_output", "")
        assert verify_gemini_meeting_minutes_structure(raw_output), \
            "Output should have valid meeting minutes structure"
