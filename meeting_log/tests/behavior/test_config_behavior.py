"""Behavior tests for configuration management.

Tests WHAT the Config does, not HOW it works internally.
Following Kent Beck's TDD principles (Chicago School):
- Tests observable outcomes only (validation results, directory creation)
- Focuses on public interface (validate, setup_directories)
- Enables refactoring-safe tests

Config Behavior Tested:
- validate(): Returns errors for missing required keys
- setup_directories(): Creates necessary directories

Fixtures used:
- monkeypatch: Pytest fixture for mocking environment
- tmp_path: Pytest fixture for temporary directories
"""

import pytest
from unittest.mock import patch
from config import Config


class TestConfigValidation:
    """Behavior: Config validates required API keys.

    Tests focus on observable validation outcomes,
    not on internal implementation details.
    """

    def test_validate_with_all_keys_present(self):
        """Test that validation passes when all required keys are set.

        Behavior tested:
        - Returns empty list when all keys present
        - No errors reported
        - System is ready to use
        """
        # Given: All required keys are set
        with patch.object(Config, 'GEMINI_API_KEY', 'test_gemini_key'), \
             patch.object(Config, 'NOTION_TOKEN', 'test_notion_token'), \
             patch.object(Config, 'NOTION_PAGE_ID', 'test_page_id'):

            # When: Validate configuration
            errors = Config.validate()

            # Then: Should have no errors
            assert errors == []
            assert len(errors) == 0

    def test_validate_missing_gemini_api_key(self):
        """Test that validation fails when GEMINI_API_KEY is missing.

        Behavior tested:
        - Returns error message for missing GEMINI_API_KEY
        - Error message is descriptive
        - Only one error (other keys are present)
        """
        # Given: GEMINI_API_KEY is missing, others present
        with patch.object(Config, 'GEMINI_API_KEY', ''), \
             patch.object(Config, 'NOTION_TOKEN', 'test_token'), \
             patch.object(Config, 'NOTION_PAGE_ID', 'test_page_id'):

            # When: Validate configuration
            errors = Config.validate()

            # Then: Should report missing GEMINI_API_KEY
            assert "GEMINI_API_KEY is not set" in errors
            assert len(errors) == 1

    def test_validate_missing_notion_token(self):
        """Test that validation fails when NOTION_TOKEN is missing.

        Behavior tested:
        - Returns error message for missing NOTION_TOKEN
        - Error message is descriptive
        - Only one error (other keys are present)
        """
        # Given: NOTION_TOKEN is missing, others present
        with patch.object(Config, 'GEMINI_API_KEY', 'test_key'), \
             patch.object(Config, 'NOTION_TOKEN', ''), \
             patch.object(Config, 'NOTION_PAGE_ID', 'test_page_id'):

            # When: Validate configuration
            errors = Config.validate()

            # Then: Should report missing NOTION_TOKEN
            assert "NOTION_TOKEN is not set" in errors
            assert len(errors) == 1

    def test_validate_missing_notion_page_id(self):
        """Test that validation fails when NOTION_PAGE_ID is missing.

        Behavior tested:
        - Returns error message for missing NOTION_PAGE_ID
        - Error message is descriptive
        - Only one error (other keys are present)
        """
        # Given: NOTION_PAGE_ID is missing, others present
        with patch.object(Config, 'GEMINI_API_KEY', 'test_key'), \
             patch.object(Config, 'NOTION_TOKEN', 'test_token'), \
             patch.object(Config, 'NOTION_PAGE_ID', ''):

            # When: Validate configuration
            errors = Config.validate()

            # Then: Should report missing NOTION_PAGE_ID
            assert "NOTION_PAGE_ID is not set" in errors
            assert len(errors) == 1

    def test_validate_multiple_missing_keys(self):
        """Test that validation reports all missing keys.

        Behavior tested:
        - Returns all errors when multiple keys missing
        - Each missing key has its own error message
        - All required keys are checked
        """
        # Given: All required keys are missing
        with patch.object(Config, 'GEMINI_API_KEY', ''), \
             patch.object(Config, 'NOTION_TOKEN', ''), \
             patch.object(Config, 'NOTION_PAGE_ID', ''):

            # When: Validate configuration
            errors = Config.validate()

            # Then: Should report all missing keys
            assert len(errors) == 3
            assert "GEMINI_API_KEY is not set" in errors
            assert "NOTION_TOKEN is not set" in errors
            assert "NOTION_PAGE_ID is not set" in errors


class TestConfigDirectorySetup:
    """Behavior: Config creates necessary directories.

    Tests focus on observable directory creation outcomes,
    not on internal implementation details.
    """

    def test_setup_directories_creates_upload_dir(self, tmp_path):
        """Test that setup_directories creates UPLOAD_DIR.

        Behavior tested:
        - Creates UPLOAD_DIR if it doesn't exist
        - Directory is accessible after creation
        - No errors when creating new directory
        """
        # Given: UPLOAD_DIR doesn't exist yet
        test_upload_dir = tmp_path / "test_uploads"

        with patch.object(Config, 'UPLOAD_DIR', test_upload_dir):
            # Directory should not exist yet
            assert not test_upload_dir.exists()

            # When: Setup directories
            Config.setup_directories()

            # Then: Directory should be created
            assert test_upload_dir.exists()
            assert test_upload_dir.is_dir()

    def test_setup_directories_idempotent(self, tmp_path):
        """Test that setup_directories can be called multiple times safely.

        Behavior tested:
        - Multiple calls don't cause errors
        - Directory remains accessible
        - Idempotent behavior (same result regardless of calls)
        """
        # Given: A test upload directory
        test_upload_dir = tmp_path / "test_uploads"

        with patch.object(Config, 'UPLOAD_DIR', test_upload_dir):
            # When: Call setup_directories twice
            Config.setup_directories()
            Config.setup_directories()

            # Then: Directory should still exist and be usable
            assert test_upload_dir.exists()
            assert test_upload_dir.is_dir()

    def test_setup_directories_existing_dir(self, tmp_path):
        """Test that setup_directories works when directory already exists.

        Behavior tested:
        - No errors when directory already exists
        - Existing directory is preserved
        - Graceful handling of pre-existing state
        """
        # Given: Directory already exists
        test_upload_dir = tmp_path / "existing_uploads"
        test_upload_dir.mkdir()

        with patch.object(Config, 'UPLOAD_DIR', test_upload_dir):
            # When: Setup directories
            Config.setup_directories()

            # Then: Should work without errors
            assert test_upload_dir.exists()
            assert test_upload_dir.is_dir()
