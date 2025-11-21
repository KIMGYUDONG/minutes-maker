# Automated Meeting Minutes Service

A local web service for automated meeting minutes generation using Whisper (speech-to-text), Gemini Pro (LLM), and Notion API.

## 🎯 Features

- **Audio Transcription**: High-quality speech-to-text using Whisper large-v3 on GPU
- **Voice Activity Detection**: Smart silence removal using silero-VAD
- **AI-Powered Minutes**: Intelligent merging of transcript and manual notes using Gemini Pro
- **Notion Integration**: One-click export to Notion with beautiful formatting
- **Network Access**: Access from any device on your local network
- **CUDA Optimization**: Maximizes RTX 3060 performance with graceful OOM handling

## 📋 Output Format

Meeting minutes are structured into four sections:
- **📝 Summary**: High-level overview
- **🔑 Key Updates**: Important decisions and announcements
- **💬 Discussion Log**: Detailed discussion points
- **✅ Action Items**: Actionable tasks with checkboxes

## 🔧 Prerequisites

- **Python**: 3.10 or higher
- **CUDA**: 11.8+ (for GPU acceleration)
- **GPU**: NVIDIA RTX 3060 (12GB VRAM) or similar
- **API Keys**: 
  - Google Gemini Pro API key
  - Notion Integration Token
  - Notion Page ID

## 🚀 Installation

### 1. Clone or Create Project

```bash
cd c:\code\minutes_maker\meeting_log
```

### 2. Create Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:
```bash
copy .env.example .env
```

Edit `.env` and fill in your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
NOTION_TOKEN=your_notion_integration_token_here
NOTION_PAGE_ID=your_notion_page_id_here
```

#### Getting API Keys:

**Gemini Pro API Key:**
1. Visit https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and paste into `.env`

**Notion Integration:**
1. Visit https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the "Internal Integration Token"
4. Share your target Notion page with the integration
5. Copy the page ID from the page URL

## 🌐 Network Setup

### Windows PC (Server)

1. **Find your PC's IP address:**
```bash
ipconfig
```
Look for "IPv4 Address" under your active network adapter (e.g., `192.168.1.100`)

2. **Configure Windows Firewall:**
```bash
# Allow Streamlit through firewall
netsh advfirewall firewall add rule name="Streamlit" dir=in action=allow protocol=TCP localport=8501
```

### MacBook (Client)

Simply access the service using your Windows PC's IP:
```
http://192.168.1.100:8501
```

## 💻 Usage

### Start the Service

```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

The service will be available at:
- **Windows PC**: http://localhost:8501
- **MacBook**: http://<WINDOWS_PC_IP>:8501

### Using the Interface

1. **Upload Audio**: Click "Upload your meeting recording" and select an m4a, mp3, or wav file
2. **Add Manual Notes** (Optional): Paste or type any notes you took during the meeting
3. **Generate**: Click "🚀 Generate Meeting Minutes"
4. **Review & Edit**: Review the generated sections and make any edits
5. **Send to Notion**: Click "📤 Send to Notion" to create the page

## 🧠 How It Works

### Audio Processing Pipeline

1. **Format Conversion**: Converts m4a/mp3 to WAV if needed
2. **Voice Activity Detection**: silero-VAD removes silent segments
3. **Speech-to-Text**: Whisper large-v3 transcribes speech segments
4. **Error Handling**: Automatic fallback to smaller models if GPU runs out of memory

### LLM Processing

1. **Prompt Engineering**: Custom prompt instructs Gemini Pro to merge sources
2. **Prioritization**: Manual notes are treated as authoritative
3. **Enrichment**: Transcript provides additional context and details
4. **Formatting**: Output structured into four distinct sections

### Notion Integration

1. **Block Formatting**: Converts text to rich Notion blocks
2. **Page Creation**: Creates a new sub-page under your specified page
3. **Checkboxes**: Action items become interactive to-do items

## ⚙️ Configuration

### Whisper Model Selection

Default: `large-v3` (best quality, ~10GB VRAM)

To use a smaller model, edit `.env`:
```env
WHISPER_MODEL=large-v2  # or medium, small, base
```

### CUDA Memory Management

The system automatically:
- Uses FP16 precision to reduce VRAM usage
- Implements fallback to smaller models on OOM errors
- Clears GPU memory after processing

## 🐛 Troubleshooting

### GPU Not Detected

```bash
python -c "import torch; print(torch.cuda.is_available())"
```
If this returns `False`, reinstall PyTorch with CUDA support:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Connection Refused from MacBook

1. Verify Windows firewall rule is active
2. Ensure both devices are on the same network
3. Try pinging the Windows PC from MacBook: `ping <WINDOWS_PC_IP>`

### Notion API Errors

1. Verify your integration has access to the target page
2. Check that the page ID in `.env` is correct
3. Ensure the integration token is valid

## 📝 Supported Audio Formats

- **m4a** (iPhone recordings)
- **mp3**
- **wav**

Maximum file size: 500MB

## 🤝 Contributing

This is a personal project. Feel free to fork and modify for your needs.

## 📄 License

MIT License - feel free to use and modify as needed.
