def test_whisper_mock(mock_whisper):
    """Verify Whisper mock returns 'Hello World'."""
    result = mock_whisper.transcribe("dummy_audio.wav")
    assert result["text"] == "Hello World"

def test_gemini_mock(mock_gemini):
    """Verify Gemini mock returns structured markdown."""
    response = mock_gemini.generate_content("dummy prompt")
    assert "## 📝 Summary" in response.text
    assert "## 🔑 Key Updates" in response.text
    assert "## 💬 Discussion Log" in response.text
    assert "## ✅ Action Items" in response.text
