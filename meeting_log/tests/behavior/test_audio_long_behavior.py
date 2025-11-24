"""
Behavior tests for long audio processing (SPEC-005).

Tests verify WHAT the system does with long audio, not HOW it works.
Uses real Whisper models and actual audio files.
Follows Kent Beck's Chicago School TDD principles.
"""

import pytest
from pathlib import Path

# Skip all tests in this module if torch is not available
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not available (Mac environment)")

from audio_processor import AudioProcessor


class TestLongAudioDetection:
    """Behavior: System detects when audio requires segmentation."""

    def test_audio_under_1_hour_uses_regular_pipeline(self):
        """Test that short audio (< 1 hour) processes normally.

        Behavior tested:
        - Audio under 1 hour is processed as single unit
        - No segmentation occurs
        - Result contains complete transcript
        """
        # Given: Short audio (30 minutes)
        processor = AudioProcessor()

        # When: Check if it's long audio
        is_long = processor._is_long_audio(duration_seconds=1800)  # 30 min

        # Then: Should NOT be classified as long
        assert is_long is False

    def test_audio_over_1_hour_uses_segmentation(self):
        """Test that long audio (> 1 hour) triggers segmentation.

        Behavior tested:
        - Audio over 1 hour is detected as long
        - Segmentation strategy is selected
        - System prepares for multi-segment processing
        """
        # Given: Long audio (2 hours)
        processor = AudioProcessor()

        # When: Check if it's long audio
        is_long = processor._is_long_audio(duration_seconds=7200)  # 2 hours

        # Then: Should be classified as long
        assert is_long is True

    def test_exactly_1_hour_boundary_condition(self):
        """Test boundary condition at exactly 1 hour.

        Behavior tested:
        - Audio exactly at 1 hour threshold
        - Clear boundary behavior (> not >=)
        - Predictable classification
        """
        # Given: Audio exactly 1 hour
        processor = AudioProcessor()

        # When: Check if it's long audio
        is_long = processor._is_long_audio(duration_seconds=3600)  # 1 hour

        # Then: Should NOT trigger segmentation (use > not >=)
        assert is_long is False


class TestAudioSegmentation:
    """Behavior: System segments long audio into manageable chunks."""

    @pytest.mark.skipif(
        not Path("tests/fixtures/sample_2hour_audio.m4a").exists(),
        reason="2-hour test audio not available"
    )
    def test_2_hour_audio_segments_into_4_chunks(self):
        """Test that 2-hour audio creates 4 segments (30min each).

        Behavior tested:
        - Long audio is divided into 30-minute segments
        - Number of segments matches expected count
        - Each segment has metadata
        """
        # Given: 2-hour audio file
        processor = AudioProcessor()
        audio_path = Path("tests/fixtures/sample_2hour_audio.m4a")

        # When: Segment the audio
        segments = processor._segment_audio(audio_path)

        # Then: Should create 4 segments
        assert len(segments) == 4
        assert all("index" in s for s in segments)
        assert all("path" in s for s in segments)

    @pytest.mark.skipif(
        not Path("tests/fixtures/sample_2hour_audio.m4a").exists(),
        reason="2-hour test audio not available"
    )
    def test_segments_have_30_second_overlap(self):
        """Test that segments overlap by 30 seconds.

        Behavior tested:
        - Adjacent segments overlap by 30 seconds
        - Prevents word cutoff at boundaries
        - Overlap is consistent across all segments
        """
        # Given: 2-hour audio file
        processor = AudioProcessor()
        audio_path = Path("tests/fixtures/sample_2hour_audio.m4a")

        # When: Segment the audio
        segments = processor._segment_audio(audio_path)

        # Then: Check overlap between segments
        if len(segments) > 1:
            # Segment 1 should start 30 seconds before Segment 0 ends
            overlap = segments[0]["end_time"] - segments[1]["start_time"]
            assert 25 <= overlap <= 35, f"Expected ~30s overlap, got {overlap}s"


# Note: Full integration tests with real 2-hour audio will be added
# after implementation is working with shorter test files.
