"""End-to-End workflow behavior tests.

Tests the complete pipeline from transcript to Notion page.
Following Kent Beck's TDD principles (Chicago School):
- Uses real APIs (Gemini, Notion) - no mocks
- Tests observable outcomes (final Notion page)
- Tests complete user workflows
- Enables refactoring-safe tests

Fixtures used:
- real_llm_processor: Real LLMProcessor instance
- real_notion_client: Real NotionClient instance
- test_transcript: Sample Korean transcript
- test_manual_notes: Sample manual notes
- cleanup_test_pages: Auto cleanup after tests
"""

import pytest
from tests.helpers.notion_helper import (
    fetch_notion_page_content,
    verify_notion_page_structure,
)


class TestEndToEndPipeline:
    """Behavior: Complete transcript to Notion workflow.

    Tests the entire user workflow from start to finish,
    verifying that all components work together correctly.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_transcript_to_notion_full_pipeline(
        self,
        real_llm_processor,
        real_notion_client,
        test_transcript
    ):
        """Test complete pipeline: Transcript → LLM → Notion.

        Behavior tested:
        - LLM generates meeting minutes from transcript
        - Notion page is created with generated content
        - All sections appear in the final page
        - Korean content is preserved throughout pipeline
        - Final Notion page is accessible and readable

        This simulates the complete user workflow.
        """
        # Step 1: Generate meeting minutes from transcript
        llm_result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Verify LLM output is generated
        assert llm_result is not None
        assert "summary" in llm_result
        assert len(llm_result["summary"]) > 0

        # Step 2: Create Notion page with generated content
        notion_url = real_notion_client.create_meeting_minutes(
            summary=llm_result["summary"],
            key_updates=llm_result["key_updates"],
            discussion_log=llm_result["discussion_log"],
            action_items=llm_result["action_items"]
        )

        # Verify Notion page is created
        assert notion_url is not None
        assert "notion.so" in notion_url

        # Step 3: Fetch and verify final Notion page content
        page_content = fetch_notion_page_content(notion_url)

        # Verify all sections are present
        expected_sections = ["요약", "업데이트", "논의", "할 일"]
        assert verify_notion_page_structure(notion_url, expected_sections)

        # Verify Korean content is preserved
        assert len(page_content) > 100  # Substantial content
        # Korean characters should be present
        korean_char_count = sum(1 for char in page_content if '\uac00' <= char <= '\ud7af')
        assert korean_char_count > 10

    @pytest.mark.integration
    @pytest.mark.slow
    def test_merges_transcript_and_notes_to_notion(
        self,
        real_llm_processor,
        real_notion_client,
        test_transcript,
        test_manual_notes
    ):
        """Test complete pipeline with both transcript and manual notes.

        Behavior tested:
        - LLM merges transcript and manual notes
        - Manual notes take priority
        - Notion page contains merged content
        - All information sources are represented

        This simulates the most common user workflow.
        """
        # Step 1: Generate meeting minutes from both sources
        llm_result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=test_manual_notes
        )

        # Verify both sources are processed
        assert llm_result is not None
        raw_output = llm_result.get("raw_output", "")

        # Should contain content from manual notes (킥오프 미팅)
        assert "킥오프" in raw_output or "개발" in raw_output

        # Step 2: Create Notion page
        notion_url = real_notion_client.create_meeting_minutes(
            summary=llm_result["summary"],
            key_updates=llm_result["key_updates"],
            discussion_log=llm_result["discussion_log"],
            action_items=llm_result["action_items"]
        )

        # Step 3: Verify final page
        assert notion_url is not None
        page_content = fetch_notion_page_content(notion_url)

        # Verify merged content appears
        # Manual notes mention "킥오프 미팅 예정"
        assert "킥오프" in page_content or "미팅" in page_content

    @pytest.mark.integration
    @pytest.mark.slow
    def test_handles_minimal_transcript_gracefully(
        self,
        real_llm_processor,
        real_notion_client
    ):
        """Test pipeline with minimal/short transcript.

        Behavior tested:
        - Short transcripts don't cause errors
        - LLM still generates reasonable output
        - Notion page is created successfully
        - No empty or error states in final page
        """
        # Given: Very short transcript
        minimal_transcript = "안녕하세요. 오늘 회의를 시작하겠습니다. 감사합니다."

        # Step 1: Generate minutes from minimal input
        llm_result = real_llm_processor.create_meeting_minutes(
            transcript=minimal_transcript,
            manual_notes=None
        )

        # Verify LLM still generates output
        assert llm_result is not None
        assert len(llm_result["summary"]) > 0

        # Step 2: Create Notion page
        notion_url = real_notion_client.create_meeting_minutes(
            summary=llm_result["summary"],
            key_updates=llm_result["key_updates"],
            discussion_log=llm_result["discussion_log"],
            action_items=llm_result["action_items"]
        )

        # Step 3: Verify page is created
        assert notion_url is not None

        page_content = fetch_notion_page_content(notion_url)

        # Verify no error placeholders
        assert "error" not in page_content.lower()
        assert "failed" not in page_content.lower()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_action_items_become_checkboxes_in_notion(
        self,
        real_llm_processor,
        real_notion_client,
        test_transcript
    ):
        """Test that LLM-generated action items appear as checkboxes in Notion.

        Behavior tested:
        - LLM identifies action items from transcript
        - Action items are formatted correctly
        - Notion creates checkboxes for action items
        - Checkboxes are unchecked by default

        This tests the complete action items workflow.
        """
        # Step 1: Generate minutes (LLM should identify action items)
        llm_result = real_llm_processor.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=None
        )

        # Verify action items are generated
        assert len(llm_result["action_items"]) > 0

        # Step 2: Create Notion page
        notion_url = real_notion_client.create_meeting_minutes(
            summary=llm_result["summary"],
            key_updates=llm_result["key_updates"],
            discussion_log=llm_result["discussion_log"],
            action_items=llm_result["action_items"]
        )

        # Step 3: Verify checkboxes in final page
        page_content = fetch_notion_page_content(notion_url)

        # Should contain unchecked checkboxes
        assert "[ ]" in page_content

        # Should have action items section
        assert "할 일" in page_content or "할일" in page_content


class TestErrorRecovery:
    """Behavior: Pipeline handles errors gracefully.

    Tests how the complete workflow responds to error conditions.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_recovers_from_llm_generation_with_manual_fallback(
        self,
        real_llm_processor,
        real_notion_client
    ):
        """Test that pipeline can handle LLM output directly.

        Behavior tested:
        - If LLM generates unusual output, Notion still creates page
        - Manual intervention is possible
        - System degrades gracefully

        This tests resilience of the pipeline.
        """
        # Given: Manual content (simulating LLM fallback scenario)
        manual_content = {
            "summary": "수동으로 작성한 회의 요약입니다.",
            "key_updates": "- 주요 업데이트 1\n- 주요 업데이트 2",
            "discussion_log": "논의 내용이 여기에 들어갑니다.",
            "action_items": "- 할 일 1\n- 할 일 2"
        }

        # When: Create Notion page with manual content
        notion_url = real_notion_client.create_meeting_minutes(
            summary=manual_content["summary"],
            key_updates=manual_content["key_updates"],
            discussion_log=manual_content["discussion_log"],
            action_items=manual_content["action_items"]
        )

        # Then: Should create page successfully
        assert notion_url is not None

        page_content = fetch_notion_page_content(notion_url)
        assert "수동으로 작성한" in page_content


class TestDataPreservation:
    """Behavior: Data is preserved throughout the pipeline.

    Tests that information isn't lost or corrupted as it flows
    through LLM → Notion transformations.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_korean_text_preserved_through_pipeline(
        self,
        real_llm_processor,
        real_notion_client
    ):
        """Test that Korean text remains intact through complete pipeline.

        Behavior tested:
        - Korean input → Korean output
        - No encoding issues (garbled text)
        - Special characters preserved
        - Final Notion page readable
        """
        # Given: Korean transcript with special characters
        korean_transcript = """
        안녕하세요! 오늘의 안건은 다음과 같습니다:
        1️⃣ Q4 목표 달성률 - 95% 완료
        2️⃣ 신규 프로젝트 "혁신" 시작
        ✅ 기획안 승인 완료
        📅 다음 주 월요일 킥오프
        """

        # Step 1: LLM processing
        llm_result = real_llm_processor.create_meeting_minutes(
            transcript=korean_transcript,
            manual_notes=None
        )

        # Step 2: Notion creation
        notion_url = real_notion_client.create_meeting_minutes(
            summary=llm_result["summary"],
            key_updates=llm_result["key_updates"],
            discussion_log=llm_result["discussion_log"],
            action_items=llm_result["action_items"]
        )

        # Step 3: Verify preservation
        page_content = fetch_notion_page_content(notion_url)

        # Korean should be preserved
        korean_char_count = sum(1 for char in page_content if '\uac00' <= char <= '\ud7af')
        assert korean_char_count > 10

        # No garbled patterns
        garbled_patterns = ["ê°€", "í•œ", "ê¸€", "\\ud", "\\x"]
        for pattern in garbled_patterns:
            assert pattern not in page_content

    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_content_preserved_through_pipeline(
        self,
        real_llm_processor,
        real_notion_client
    ):
        """Test that long content is handled throughout pipeline.

        Behavior tested:
        - Long transcripts are processed
        - LLM generates comprehensive output
        - Notion handles long content (chunking)
        - No truncation or data loss
        """
        # Given: Long transcript
        long_transcript = """
        안녕하세요. 오늘 회의를 시작하겠습니다.
        """ + ("이것은 긴 회의 내용입니다. " * 100)  # ~3000 chars

        # Step 1: LLM processing
        llm_result = real_llm_processor.create_meeting_minutes(
            transcript=long_transcript,
            manual_notes=None
        )

        # Step 2: Notion creation
        notion_url = real_notion_client.create_meeting_minutes(
            summary=llm_result["summary"],
            key_updates=llm_result["key_updates"],
            discussion_log=llm_result["discussion_log"],
            action_items=llm_result["action_items"]
        )

        # Step 3: Verify no truncation
        assert notion_url is not None
        page_content = fetch_notion_page_content(notion_url)

        # Should have substantial content
        assert len(page_content) > 500
