import pytest
from pathlib import Path

# Conditional imports for torch/torchaudio/audio_processor
try:
    import torch
    import torchaudio
    from audio_processor import AudioProcessor
    HAS_TORCH = True
    HAS_CUDA = torch.cuda.is_available()
except ImportError:
    HAS_TORCH = False
    HAS_CUDA = False
    AudioProcessor = None

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not available (Mac environment)")

@pytest.mark.skipif(not HAS_CUDA, reason="CUDA not available, skipping GPU precision test")
def test_transcription_precision_safety(tmp_path):
    """
    Test Case Name: test_transcription_precision_safety
    Scenario:
        Load the Whisper model on CUDA.
        Generate a dummy audio tensor.
        Run transcribe() method.
    Assertion: 
        It should run successfully without raising RuntimeError (specifically Float vs Half).
    """
    # 1. Setup dummy audio file
    sample_rate = 16000
    duration_sec = 1
    waveform = torch.randn(1, sample_rate * duration_sec)
    audio_path = tmp_path / "test_precision.wav"
    
    # Ensure backend is set (just in case)
    try:
        torchaudio.set_audio_backend("soundfile")
    except:
        pass
        
    torchaudio.save(str(audio_path), waveform, sample_rate)
    
    # 2. Initialize AudioProcessor
    processor = AudioProcessor()
    
    # Mock _apply_vad to return a dummy timestamp so we proceed to transcription
    # even if the random noise isn't detected as speech.
    # We want to test the Whisper transcription step, not VAD.
    processor._apply_vad = lambda x: [{"start": 0, "end": 1}]
    
    # 3. Run transcribe
    try:
        # This will load the model (downloading if necessary, but likely cached)
        # and attempt transcription.
        result = processor.transcribe(audio_path)
        
        # 4. Assertions
        assert "text" in result
        assert "segments" in result
        
    except RuntimeError as e:
        # Fail specifically if it's the precision error
        error_msg = str(e)
        if "expected scalar type Float but found Half" in error_msg:
            pytest.fail(f"Caught FP16 precision error: {error_msg}")
        else:
            # Re-raise other errors (e.g. OOM)
            raise e
