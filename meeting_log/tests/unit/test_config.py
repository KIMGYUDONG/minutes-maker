"""Tests for configuration management."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch
from config import Config


class TestConfigEnvironmentVariables:
    """Test configuration loading from environment variables."""

    def test_gemini_api_key_from_env(self, monkeypatch):
        """Test GEMINI_API_KEY loaded from environment."""
        test_key = "test_gemini_key_123"
        monkeypatch.setenv("GEMINI_API_KEY", test_key)

        # Need to reload module to pick up new env vars
        with patch.dict(os.environ, {"GEMINI_API_KEY": test_key}):
            from importlib import reload
            import config
            reload(config)

            assert config.Config.GEMINI_API_KEY == test_key

    def test_gemini_model_name_default(self):
        """Test GEMINI_MODEL_NAME has correct default value."""
        # Should be gemini-2.5-pro as the default
        assert Config.GEMINI_MODEL_NAME in ["gemini-2.5-pro", os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-pro")]

    def test_whisper_model_defaults(self):
        """Test Whisper model configuration defaults."""
        assert Config.WHISPER_MODEL in ["large-v3", os.getenv("WHISPER_MODEL", "large-v3")]
        assert Config.WHISPER_FALLBACK_MODEL in ["large-v2", os.getenv("WHISPER_FALLBACK_MODEL", "large-v2")]

    def test_streamlit_server_defaults(self):
        """Test Streamlit server configuration defaults."""
        assert Config.STREAMLIT_SERVER_ADDRESS in ["0.0.0.0", os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")]
        assert Config.STREAMLIT_SERVER_PORT == int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))


class TestConfigConstants:
    """Test configuration constants."""

    def test_supported_formats(self):
        """Test supported audio formats list."""
        assert Config.SUPPORTED_FORMATS == [".m4a", ".mp3", ".wav"]
        assert ".m4a" in Config.SUPPORTED_FORMATS
        assert ".mp3" in Config.SUPPORTED_FORMATS
        assert ".wav" in Config.SUPPORTED_FORMATS

    def test_max_file_size(self):
        """Test maximum file size configuration."""
        assert Config.MAX_FILE_SIZE_MB == 500
        assert isinstance(Config.MAX_FILE_SIZE_MB, int)

    def test_vad_configuration(self):
        """Test VAD (Voice Activity Detection) configuration."""
        assert Config.VAD_SAMPLE_RATE == 16000
        assert Config.VAD_THRESHOLD == 0.5
        assert Config.VAD_MIN_SPEECH_MS == 250
        assert Config.VAD_MIN_SILENCE_MS == 500

    def test_vad_values_are_correct_types(self):
        """Test VAD values have correct types."""
        assert isinstance(Config.VAD_SAMPLE_RATE, int)
        assert isinstance(Config.VAD_THRESHOLD, float)
        assert isinstance(Config.VAD_MIN_SPEECH_MS, int)
        assert isinstance(Config.VAD_MIN_SILENCE_MS, int)


class TestConfigPaths:
    """Test path configuration."""

    def test_base_dir_is_path(self):
        """Test BASE_DIR is a Path object."""
        assert isinstance(Config.BASE_DIR, Path)

    def test_base_dir_exists(self):
        """Test BASE_DIR points to an existing directory."""
        assert Config.BASE_DIR.exists()
        assert Config.BASE_DIR.is_dir()

    def test_upload_dir_is_relative_to_base(self):
        """Test UPLOAD_DIR is relative to BASE_DIR."""
        assert Config.UPLOAD_DIR == Config.BASE_DIR / "uploads"

    def test_upload_dir_is_path(self):
        """Test UPLOAD_DIR is a Path object."""
        assert isinstance(Config.UPLOAD_DIR, Path)


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_with_all_keys_present(self):
        """Test validation passes when all required keys are set."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test_key'), \
             patch.object(Config, 'NOTION_TOKEN', 'test_token'), \
             patch.object(Config, 'NOTION_PAGE_ID', 'test_page_id'):

            errors = Config.validate()

            assert errors == []
            assert len(errors) == 0

    def test_validate_missing_gemini_api_key(self):
        """Test validation fails when GEMINI_API_KEY is missing."""
        with patch.object(Config, 'GEMINI_API_KEY', ''), \
             patch.object(Config, 'NOTION_TOKEN', 'test_token'), \
             patch.object(Config, 'NOTION_PAGE_ID', 'test_page_id'):

            errors = Config.validate()

            assert "GEMINI_API_KEY is not set" in errors
            assert len(errors) == 1

    def test_validate_missing_notion_token(self):
        """Test validation fails when NOTION_TOKEN is missing."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test_key'), \
             patch.object(Config, 'NOTION_TOKEN', ''), \
             patch.object(Config, 'NOTION_PAGE_ID', 'test_page_id'):

            errors = Config.validate()

            assert "NOTION_TOKEN is not set" in errors
            assert len(errors) == 1

    def test_validate_missing_notion_page_id(self):
        """Test validation fails when NOTION_PAGE_ID is missing."""
        with patch.object(Config, 'GEMINI_API_KEY', 'test_key'), \
             patch.object(Config, 'NOTION_TOKEN', 'test_token'), \
             patch.object(Config, 'NOTION_PAGE_ID', ''):

            errors = Config.validate()

            assert "NOTION_PAGE_ID is not set" in errors
            assert len(errors) == 1

    def test_validate_multiple_missing_keys(self):
        """Test validation reports all missing keys."""
        with patch.object(Config, 'GEMINI_API_KEY', ''), \
             patch.object(Config, 'NOTION_TOKEN', ''), \
             patch.object(Config, 'NOTION_PAGE_ID', ''):

            errors = Config.validate()

            assert len(errors) == 3
            assert "GEMINI_API_KEY is not set" in errors
            assert "NOTION_TOKEN is not set" in errors
            assert "NOTION_PAGE_ID is not set" in errors

    def test_validate_returns_list(self):
        """Test validate() always returns a list."""
        result = Config.validate()

        assert isinstance(result, list)


class TestConfigSetupDirectories:
    """Test directory setup functionality."""

    def test_setup_directories_creates_upload_dir(self, tmp_path):
        """Test setup_directories creates UPLOAD_DIR."""
        # Temporarily change UPLOAD_DIR to a test path
        test_upload_dir = tmp_path / "test_uploads"

        with patch.object(Config, 'UPLOAD_DIR', test_upload_dir):
            # Directory should not exist yet
            assert not test_upload_dir.exists()

            # Call setup_directories
            Config.setup_directories()

            # Directory should now exist
            assert test_upload_dir.exists()
            assert test_upload_dir.is_dir()

    def test_setup_directories_idempotent(self, tmp_path):
        """Test setup_directories can be called multiple times safely."""
        test_upload_dir = tmp_path / "test_uploads"

        with patch.object(Config, 'UPLOAD_DIR', test_upload_dir):
            # Call setup_directories twice
            Config.setup_directories()
            Config.setup_directories()

            # Directory should still exist
            assert test_upload_dir.exists()

    def test_setup_directories_existing_dir(self, tmp_path):
        """Test setup_directories works when directory already exists."""
        test_upload_dir = tmp_path / "existing_uploads"
        test_upload_dir.mkdir()

        with patch.object(Config, 'UPLOAD_DIR', test_upload_dir):
            # Should not raise error even though directory exists
            Config.setup_directories()

            assert test_upload_dir.exists()


class TestConfigEdgeCases:
    """Test edge cases and special scenarios."""

    def test_streamlit_port_is_integer(self):
        """Test STREAMLIT_SERVER_PORT is always an integer."""
        assert isinstance(Config.STREAMLIT_SERVER_PORT, int)

    def test_supported_formats_immutable_list(self):
        """Test SUPPORTED_FORMATS list contains expected values."""
        # Make a copy and verify it matches
        formats_copy = Config.SUPPORTED_FORMATS.copy()

        assert formats_copy == [".m4a", ".mp3", ".wav"]

    def test_vad_threshold_in_valid_range(self):
        """Test VAD_THRESHOLD is between 0 and 1."""
        assert 0.0 <= Config.VAD_THRESHOLD <= 1.0

    def test_vad_durations_positive(self):
        """Test VAD duration values are positive."""
        assert Config.VAD_MIN_SPEECH_MS > 0
        assert Config.VAD_MIN_SILENCE_MS > 0

    def test_max_file_size_reasonable(self):
        """Test MAX_FILE_SIZE_MB is reasonable."""
        assert Config.MAX_FILE_SIZE_MB > 0
        assert Config.MAX_FILE_SIZE_MB <= 10000  # Not more than 10GB


class TestConfigUsage:
    """Test typical configuration usage patterns."""

    def test_config_can_be_imported(self):
        """Test Config can be imported successfully."""
        from config import Config as ImportedConfig

        assert ImportedConfig is not None
        assert hasattr(ImportedConfig, 'GEMINI_API_KEY')
        assert hasattr(ImportedConfig, 'validate')

    def test_config_attributes_accessible(self):
        """Test all configuration attributes are accessible."""
        # API keys
        assert hasattr(Config, 'GEMINI_API_KEY')
        assert hasattr(Config, 'GEMINI_MODEL_NAME')
        assert hasattr(Config, 'NOTION_TOKEN')
        assert hasattr(Config, 'NOTION_PAGE_ID')

        # Whisper
        assert hasattr(Config, 'WHISPER_MODEL')
        assert hasattr(Config, 'WHISPER_FALLBACK_MODEL')

        # Server
        assert hasattr(Config, 'STREAMLIT_SERVER_ADDRESS')
        assert hasattr(Config, 'STREAMLIT_SERVER_PORT')

        # Audio
        assert hasattr(Config, 'SUPPORTED_FORMATS')
        assert hasattr(Config, 'MAX_FILE_SIZE_MB')

        # VAD
        assert hasattr(Config, 'VAD_SAMPLE_RATE')
        assert hasattr(Config, 'VAD_THRESHOLD')
        assert hasattr(Config, 'VAD_MIN_SPEECH_MS')
        assert hasattr(Config, 'VAD_MIN_SILENCE_MS')

        # Paths
        assert hasattr(Config, 'BASE_DIR')
        assert hasattr(Config, 'UPLOAD_DIR')

    def test_config_methods_callable(self):
        """Test configuration methods are callable."""
        assert callable(Config.validate)
        assert callable(Config.setup_directories)
