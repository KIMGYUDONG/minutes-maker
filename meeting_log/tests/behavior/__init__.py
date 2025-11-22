"""Behavior tests for Meeting Minutes Maker.

This module contains behavior-focused tests following Kent Beck's TDD principles:
- Tests WHAT the code does, not HOW it works
- Uses real API calls (Notion, Gemini) instead of mocks
- Tests observable outcomes from public interfaces only
- Enables refactoring without breaking tests

Test Structure:
- test_notion_behavior.py: Notion page creation and formatting behavior
- test_llm_behavior.py: Gemini meeting minutes generation behavior
- test_full_workflow_behavior.py: End-to-end pipeline tests

Fixtures from conftest.py:
- real_notion_client: Real NotionClient (no mocks)
- real_llm_processor: Real LLMProcessor (no mocks)
- test_meeting_data: Sample meeting data
- test_transcript: Sample Korean transcript
- test_manual_notes: Sample manual notes
- cleanup_test_pages: Auto cleanup after tests

Usage:
    pytest tests/behavior/                    # Run all behavior tests
    pytest tests/behavior/ -m integration     # Run only integration tests
    pytest tests/behavior/ -m "not slow"      # Skip slow tests
"""
