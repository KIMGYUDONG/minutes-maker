import pytest
from unittest.mock import MagicMock, patch

# Conditional imports for torch and audio_processor
try:
    import torch
    from audio_processor import AudioProcessor
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    AudioProcessor = None

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not available (Mac environment)")

def test_transcribe_mock(mock_whisper, tmp_path):
    """
    Test transcribe() using the mocked Whisper model.
    Verify it handles file loading and returns expected structure.
    """
    # Create a dummy wav file
    audio_path = tmp_path / "test.wav"
    # Create a minimal valid wav file or just mock the file existence/loading
    # Since we mock _convert_to_wav and _apply_vad, we don't need a real audio file
    # if we patch those methods.
    
    processor = AudioProcessor()
    
    # Mock internal methods to isolate transcribe logic
    processor._convert_to_wav = MagicMock(return_value=audio_path)
    processor._apply_vad = MagicMock(return_value=[{"start": 0, "end": 1}])
    
    # Run transcribe
    result = processor.transcribe(audio_path)
    
    # Assertions
    assert result["text"] == "Hello World"
    assert "segments" in result
    assert result["model_used"] == "large-v3" # Default from config

def test_apply_vad_mock(tmp_path):
    """
    Test _apply_vad() with dummy audio.
    """
    processor = AudioProcessor()
    
    # Mock torchaudio.load to return random noise
    with patch("torchaudio.load") as mock_load:
        # Return (waveform, sample_rate)
        mock_load.return_value = (torch.randn(1, 16000), 16000)
        
        # Mock VAD model loading and execution
        processor.vad_model = MagicMock()
        
        # Patch get_speech_timestamps
        with patch("audio_processor.get_speech_timestamps") as mock_get_timestamps:
            mock_get_timestamps.return_value = [{"start": 0, "end": 16000}]
            
            timestamps = processor._apply_vad(tmp_path / "dummy.wav")
            
            assert len(timestamps) == 1
            assert timestamps[0]["start"] == 0
