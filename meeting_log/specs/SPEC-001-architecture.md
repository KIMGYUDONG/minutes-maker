# SPEC-001: System Architecture

**Status**: Implemented
**Version**: 1.0
**Last Updated**: 2025-11-22
**Owner**: Meeting Minutes Team

---

## Overview

The Meeting Minutes Generator is an AI-powered system that automatically transcribes meeting audio recordings and generates structured meeting minutes in Korean, then publishes them to Notion.

## System Architecture

```
┌─────────────────┐
│  User (Browser) │
│   Streamlit UI  │
└────────┬────────┘
         │
         ├── Upload Audio (m4a, mp3, wav)
         ├── Provide Manual Notes (optional)
         └── Edit Generated Minutes
         │
         v
┌────────────────────────────────────────────────────┐
│              Main Application (app.py)              │
│   - File Upload & Validation                       │
│   - Workflow Orchestration                         │
│   - Progress Tracking                              │
│   - Session State Management                       │
└─────────┬──────────────────────────┬───────────────┘
          │                          │
          v                          v
┌─────────────────────┐    ┌─────────────────────┐
│  Audio Processor    │    │   LLM Processor     │
│  (Whisper + VAD)    │    │  (Gemini Pro 2.5)   │
│                     │    │                     │
│  - Format Convert   │    │  - Prompt Build     │
│  - VAD Detection    │    │  - Minutes Generate │
│  - Transcription    │    │  - Response Parse   │
│  - GPU Management   │    │  - Korean Output    │
└─────────────────────┘    └──────────┬──────────┘
                                      │
                                      v
                            ┌─────────────────────┐
                            │ Notion Integration  │
                            │  (Notion API)       │
                            │                     │
                            │  - Page Creation    │
                            │  - Block Building   │
                            │  - Korean Sections  │
                            │  - Text Chunking    │
                            └─────────────────────┘
```

## Core Components

### 1. Streamlit UI (app.py)
**Purpose**: User interface and workflow orchestration

**Responsibilities**:
- File upload and validation
- Manual notes input
- Progress indication
- Minutes editing
- Notion publishing

**Key Functions**:
- `main()`: Application entry point
- `process_meeting()`: Orchestrates audio → transcript → minutes → Notion workflow
- `display_results()`: Shows generated minutes with edit capability
- `send_to_notion()`: Publishes to Notion database

### 2. Audio Processor (audio_processor.py)
**Purpose**: Audio transcription using Whisper and VAD

**Responsibilities**:
- Audio format conversion (m4a/mp3 → wav)
- Voice Activity Detection (silero-VAD)
- Speech transcription (OpenAI Whisper)
- GPU memory management

**Key Functions**:
- `transcribe()`: Main transcription pipeline
- `_convert_to_wav()`: Format conversion
- `_apply_vad()`: Speech segment detection
- `_load_whisper_model()`: Model loading with OOM handling

**Models**:
- Whisper: large-v3 (primary), large-v2 (fallback)
- silero-VAD: For speech detection

### 3. LLM Processor (llm_processor.py)
**Purpose**: Generate structured meeting minutes using LLM

**Responsibilities**:
- Prompt construction (Korean-optimized)
- LLM interaction (Google Gemini Pro 2.5)
- Response parsing (4 sections)
- Korean language output

**Key Functions**:
- `create_meeting_minutes()`: Main generation pipeline
- `_build_prompt()`: Constructs detailed Korean prompt
- `_parse_response()`: Parses LLM output into sections

**Output Sections**:
1. 요약 (Summary)
2. 업데이트 (Key Updates)
3. 논의사항 (Discussion Log)
4. 할 일 (Action Items)

### 4. Notion Integration (notion_integration.py)
**Purpose**: Publish meeting minutes to Notion database

**Responsibilities**:
- Notion page creation
- Korean section formatting
- Block structure building
- Text chunking (2000 char limit)

**Key Functions**:
- `create_meeting_minutes()`: Creates Notion page
- `_build_blocks()`: Constructs Notion block hierarchy
- `_text_to_blocks()`: Converts text to paragraphs/lists
- `_action_items_to_blocks()`: Creates to-do checkboxes

**Notion Structure**:
- Title: "팀 주간 회의 YYYY-MM-DD"
- Icon: 🧐
- Property: "제목" (Korean)
- Sections: 요약, 업데이트, 논의사항, 할 일

### 5. Configuration (config.py)
**Purpose**: Centralized configuration management

**Responsibilities**:
- Environment variable loading
- Configuration validation
- Directory setup
- Constants definition

**Key Settings**:
- Gemini API: gemini-2.5-pro
- Whisper Model: large-v3 / large-v2
- VAD Configuration
- File size/format limits

### 6. Utilities (utils.py)
**Purpose**: Shared utility functions

**Functions**:
- `validate_audio_file()`: File validation
- `format_timestamp()`: Time formatting
- `format_error_message()`: Error message formatting
- `chunk_text()`: Text chunking for Notion API

## Data Flow

### Complete Workflow

```
1. User Upload
   ├── Audio File (m4a/mp3/wav)
   └── Manual Notes (optional)

2. Audio Processing
   ├── Convert to WAV (if needed)
   ├── Apply VAD (detect speech segments)
   ├── Transcribe with Whisper
   └── Output: Transcript text + segments

3. LLM Processing
   ├── Build Korean prompt
   ├── Merge transcript + manual notes
   ├── Generate with Gemini Pro 2.5
   └── Parse into 4 sections

4. User Editing
   ├── Display in Streamlit
   ├── Allow section editing
   └── Get user approval

5. Notion Publishing
   ├── Create page in database
   ├── Build Korean section blocks
   ├── Chunk long text
   └── Return page URL
```

## Technology Stack

### Frontend
- **Streamlit**: Web UI framework
- **Python 3.14+**: Programming language

### AI/ML
- **OpenAI Whisper**: Speech-to-text (large-v3)
- **silero-VAD**: Voice Activity Detection
- **PyTorch**: Deep learning framework
- **Google Gemini Pro 2.5**: LLM for minutes generation

### Integration
- **Notion API**: Document management
- **google-generativeai**: Gemini SDK
- **notion-client**: Notion Python SDK

### Audio Processing
- **pydub**: Audio format conversion
- **torchaudio**: Audio I/O
- **soundfile**: Cross-platform audio backend

## Deployment Environment

### Development
- **Client**: MacBook (code editing, git push)
- **Server**: Windows Desktop (Streamlit server, git pull)
- **GPU**: NVIDIA RTX 3060 12GB (for Whisper)

### Requirements
- Python 3.11+
- CUDA-capable GPU (recommended for Whisper)
- 12GB+ VRAM for large-v3 model
- Internet connection (for Gemini and Notion APIs)

## Configuration

### Environment Variables (.env)
```bash
GEMINI_API_KEY=<your_key>
GEMINI_MODEL_NAME=gemini-2.5-pro
NOTION_TOKEN=<your_token>
NOTION_PAGE_ID=<database_id>
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_PORT=8501
WHISPER_MODEL=large-v3
WHISPER_FALLBACK_MODEL=large-v2
```

### File Limits
- Max file size: 100MB
- Supported formats: .m4a, .mp3, .wav
- Notion text chunk: 2000 characters

## Error Handling

### Audio Processing
- **OOM Error**: Automatic fallback to smaller Whisper model
- **Format Error**: Convert to WAV automatically
- **No Speech**: Warning message, graceful exit

### LLM Processing
- **API Error**: Display error with details
- **Parsing Error**: Use raw output as fallback

### Notion Integration
- **API Error**: Display error, preserve edited content
- **Text Too Long**: Automatic chunking

## Performance

### Optimization Strategies
1. **GPU Utilization**: Whisper runs on CUDA when available
2. **VAD Preprocessing**: Reduces transcription time by filtering silence
3. **Model Caching**: Whisper model loaded once, reused
4. **Async Not Used**: Streamlit handles UI updates synchronously

### Expected Performance
- Audio transcription: ~1-2x real-time (with GPU)
- LLM generation: 10-30 seconds
- Notion publishing: 2-5 seconds

## Security Considerations

### Credentials
- API keys stored in .env (gitignored)
- Notion token requires workspace integration
- Gemini API key requires Google Cloud account

### Data Privacy
- Audio files stored temporarily, deleted after processing
- Transcripts stored in session state only
- No persistent storage of meeting content

## Future Considerations

### Potential Enhancements
1. Speaker diarization (identify multiple speakers)
2. Real-time transcription streaming
3. Multi-language support
4. Custom LLM prompt templates
5. Export to multiple formats (PDF, DOCX)

### Scalability
- Current design: Single-user, single-meeting at a time
- Future: Multi-user support, batch processing, queue system

---

**References**:
- [OpenAI Whisper Documentation](https://github.com/openai/whisper)
- [Google Gemini API](https://ai.google.dev/)
- [Notion API Documentation](https://developers.notion.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
