import os
import pytest

# Conditional imports for torch/torchaudio
try:
    import torch
    import torchaudio
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not available (Mac environment)")

def test_load_audio(tmp_path):
    """
    Test loading an audio file.
    Action: Load a dummy wav file.
    Assertion: It should return a valid tensor array.
    """
    # Create a dummy wav file
    sample_rate = 16000
    duration_sec = 1
    # Generate random noise
    waveform = torch.randn(1, sample_rate * duration_sec)
    
    file_path = tmp_path / "test_audio.wav"
    
    # Save the dummy file
    # We need to ensure the backend is set correctly if on Windows, 
    # but audio_processor.py handles that. 
    # For this test, we might need to set it explicitly if not importing audio_processor.
    try:
        torchaudio.set_audio_backend("soundfile")
    except:
        pass
        
    torchaudio.save(str(file_path), waveform, sample_rate)
    
    # Action: Load the file
    loaded_waveform, loaded_sr = torchaudio.load(str(file_path))
    
    # Assertion
    assert isinstance(loaded_waveform, torch.Tensor)
    assert loaded_sr == sample_rate
    assert loaded_waveform.shape == waveform.shape
