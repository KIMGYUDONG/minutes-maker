# Meeting Minutes Maker

AI-powered meeting transcription and minutes generation using Whisper, Gemini Pro, and Notion.

**Methodology**: TDD + Spec Kit (Kent Beck's Chicago School)
**Platform**: Mac (development) + Windows (production with GPU)
**Testing**: 37 behavior tests with real APIs (no mocks)
**Coverage Goal**: 70%+

---

## Tech Stack

### Core Framework
- **Python**: 3.10+ (3.14 on Windows)
- **Web UI**: Streamlit 1.29.0
- **Environment**: python-dotenv 1.0.0

### AI/ML Stack
- **Speech-to-Text**: openai-whisper (large-v3 primary, large-v2 fallback)
- **Voice Detection**: silero-vad
- **LLM**: Google Gemini Pro 2.5 (google-generativeai 0.3.2)
- **Deep Learning**: PyTorch 2.1.2 + torchaudio 2.1.2 (Windows only)
- **GPU**: CUDA 11.8+, NVIDIA RTX 3060 (12GB VRAM)

### Integration
- **Document API**: notion-client 2.2.1
- **Audio**: pydub 0.25.1, soundfile (cross-platform)

### Development Tools
```
pytest>=8.0.0              # Test framework
pytest-cov>=4.1.0          # Coverage
black>=24.0.0              # Formatter
flake8>=7.0.0              # Linter
mypy>=1.8.0                # Type checker
```

---

## Project Structure

### Core Modules (6 files)
```
app.py                    - Streamlit UI & orchestration
audio_processor.py        - Whisper + VAD pipeline
llm_processor.py          - Gemini Pro integration
notion_integration.py     - Notion API client
config.py                 - Configuration & validation
utils.py                  - Shared utilities
```

### Specifications (5 specs)
```
specs/SPEC-001-architecture.md          - System design
specs/SPEC-002-audio-processing.md      - Whisper + VAD
specs/SPEC-003-llm-integration.md       - Gemini Pro
specs/SPEC-004-notion-integration.md    - Notion API
specs/SPEC-005-long-audio-support.md    - Audio segmentation
```

### Testing (37 behavior tests)
```
tests/behavior/
├── test_notion_behavior.py         (12 tests) - Real Notion API
├── test_llm_behavior.py            (11 tests) - Real Gemini API
├── test_full_workflow_behavior.py  (7 tests)  - End-to-end
├── test_config_behavior.py         (8 tests)  - Config validation
└── test_audio_long_behavior.py     (Windows only - Audio segmentation)

tests/unit/                          - Edge cases only
tests/integration/                   - Manual scripts (not pytest)
```

---

## Development Workflow (TDD + Spec Kit)

### Process: SPEC → Red → Green → Refactor → Commit

**1. Specification First**
- Create `specs/SPEC-XXX-feature.md` BEFORE any code
- Get user approval before proceeding
- Reference existing specs for format

**2. Red: Write Failing Test**
- Write ONE small failing test
- Run `pytest` to confirm failure
- Test must be specific and descriptive

**3. Green: Minimum Implementation**
- Write ONLY enough code to pass the test
- No extra features or "future-proofing"
- Run `pytest` to confirm pass

**4. Refactor: Improve Structure**
- Clean up code while keeping tests green
- Remove duplication
- Improve clarity
- Run `pytest` after each change

**5. Commit: Atomic Commits**
- Separate commits for: Spec → Test → Implementation → Refactor
- Use conventional commit prefixes

---

## Testing Commands

### Run Tests
```bash
# All behavior tests (use real APIs)
pytest tests/behavior/ -v

# Specific test modules
pytest tests/behavior/test_notion_behavior.py -v
pytest tests/behavior/test_llm_behavior.py -v
pytest tests/behavior/test_full_workflow_behavior.py -v

# With coverage report
pytest tests/behavior/ --cov=. --cov-report=html --cov-report=term-missing

# Expected results:
# Mac: 37 passed (audio tests skipped - no torch)
# Windows: 37+ passed (includes audio tests)
```

### Manual Integration Scripts (NOT pytest)
```bash
python tests/integration/test_notion_only.py
python tests/integration/test_llm_only.py
python tests/integration/test_full_workflow.py
```

### Code Quality
```bash
# Format code
black .

# Lint
flake8 .

# Type check
mypy .

# Sort imports
isort .
```

### Run Application
```bash
# Development
streamlit run app.py

# Production (Windows - expose to network)
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

---

## Commit Convention

Use conventional commit format:

```
feat:     - New features
fix:      - Bug fixes
test:     - Test additions/changes
docs:     - Documentation
refactor: - Code restructuring (no behavior change)
debug:    - Debug logging/investigation
```

**Examples**:
```
fix: Handle Gemini multi-part responses in LLM processor
test: Add test for Gemini multi-part response handling
docs: Add multi-part response handling to SPEC-003
```

---

## Code Quality Standards

### Core Principles
1. **Eliminate duplication ruthlessly**
2. **Express intent clearly** through naming
3. **Keep functions small** (single responsibility)
4. **Minimize state** and side effects
5. **Simplest solution** that could possibly work

### Coverage Goal
- **Maintain 70%+ at all times**
- Current: notion_integration.py (96%), llm_processor.py (88%)
- Track with: `pytest --cov=. --cov-report=html`

### Testing Philosophy (Kent Beck's Chicago School)
- Test WHAT the code does, not HOW it works
- Use real APIs (Notion, Gemini) - no mocks
- Focus on observable outcomes only
- Enables refactoring without breaking tests

---

## Platform-Specific Notes

### Mac (Development Environment)
- **Role**: Code editing, Git operations, TDD workflow
- **Python**: 3.14 (incompatible with torch)
- **Tests**: 37 behavior tests pass (real APIs)
- **Limitations**: No torch/torchaudio, audio tests auto-skip
- **Marker**: `@pytest.mark.skipif(not HAS_TORCH)`

### Windows (Production Environment)
- **Role**: Streamlit server, GPU processing
- **GPU**: NVIDIA RTX 3060 (12GB VRAM)
- **CUDA**: 11.8+
- **Tests**: All 37+ tests including audio/GPU
- **Network**: 0.0.0.0:8501 for Mac access

### Cross-Platform Workflow
```bash
# Mac: Develop → Test → Commit → Push
pytest tests/behavior/ -v  # 37 passed
git add .
git commit -m "feat: New feature"
git push origin main

# Windows: Pull → Test → Run
git pull origin main
pytest tests/ -v           # All tests including audio
streamlit run app.py --server.address=0.0.0.0
```

---

## Tidy First Principle

### CRITICAL RULE: Never mix structural and behavioral changes

**Structural changes** (refactor:):
- Renaming variables/functions
- Extracting methods
- Moving code
- NO behavior change

**Behavioral changes** (feat:/fix:):
- Adding functionality
- Fixing bugs
- Changing logic

**Always separate into different commits**

---

## Important "DO NOT" Rules

### Development
1. **DO NOT** mix structural + behavioral changes in one commit
2. **DO NOT** skip writing SPEC before coding
3. **DO NOT** commit without running tests
4. **DO NOT** reduce coverage below 70%
5. **DO NOT** mock real APIs in behavior tests (use real Notion/Gemini)
6. **DO NOT** future-proof or add extra features (YAGNI principle)
7. **DO NOT** create files unless absolutely necessary (prefer editing existing)

### Git
1. **DO NOT** commit sensitive data (.env, API keys)
2. **DO NOT** commit to main without tests passing
3. **DO NOT** use vague commit messages

### Code Quality
1. **DO NOT** ignore duplication
2. **DO NOT** create abstractions prematurely
3. **DO NOT** add features beyond what was requested

---

## Environment Variables

Required in `.env` (see `.env.example`):
```bash
GEMINI_API_KEY=<your_gemini_api_key>
GEMINI_MODEL_NAME=gemini-2.5-pro
NOTION_TOKEN=<your_notion_integration_token>
NOTION_PAGE_ID=<your_notion_page_id>
WHISPER_MODEL=large-v3
WHISPER_FALLBACK_MODEL=large-v2
```

---

## Data Flow Pipeline

```
1. Audio Upload (m4a/mp3/wav) + Manual Notes (optional)
   ↓
2. Audio Processor
   - Format conversion (pydub)
   - VAD segmentation (silero-vad)
   - Transcription (Whisper large-v3)
   - OOM fallback to large-v2
   ↓
3. LLM Processor (Gemini Pro 2.5)
   - Merge transcript + manual notes
   - Generate 4 sections in Korean:
     * 📝 요약 (Summary)
     * 🔑 업데이트 (Key Updates)
     * 💬 논의사항 (Discussion Log)
     * ✅ 할 일 (Action Items)
   ↓
4. User Editing (Streamlit UI)
   ↓
5. Notion Publishing
   - Create page with icon 🧐
   - Build Korean blocks
   - Chunk text (2000 char limit)
```

---

## File Size & Format Limits

- **Max file size**: 500MB
- **Supported formats**: m4a, mp3, wav
- **Notion text limit**: 2000 characters per block (auto-chunked)
- **Long audio**: > 1 hour automatically segmented into 30-min chunks

---

## Reference Documents

- **DEVELOPMENT.md**: Complete TDD + Spec Kit workflow guide (600+ lines)
- **README.md**: Project overview and setup
- **specs/**: All feature specifications (5 specs)
- **pytest.ini**: Test configuration
- **.coveragerc**: Coverage measurement settings

---

## Quick Start

```bash
# 1. Setup environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or: .\venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env with your keys

# 4. Run tests (Mac: 37 pass)
pytest tests/behavior/ -v

# 5. Start application
streamlit run app.py
```

---

## Self-Imposed AI Assistant Rules

These rules ensure reliable information and prevent misinformation.

### Rule 1: VERIFY BEFORE CLAIMING "OFFICIAL"
- **Never** claim "official" or "standard" without verification
- **Always** search documentation FIRST
- **Cite** sources with links
- **If uncertain**: "I'm not certain. Let me check the official documentation."

### Rule 2: USER QUESTIONS = VERIFICATION TRIGGER
If user asks ANY of these, IMMEDIATELY search official docs:
- "무슨 차이야?" (What's the difference?)
- "확실해?" (Are you sure?)
- "공식 문서에서 확인해줘" (Check official docs)
- "정말?" (Really?)

**Why**: User questions = they suspect I'm wrong = I probably am wrong

### Rule 3: DISTINGUISH FACTS FROM GUESSES
- **100% Certain (verified)**: "According to official docs at [link]..."
- **80% Confident (not verified)**: "Typically... but should verify"
- **50% or less (guessing)**: "I'm not sure. Let me search."

### Rule 4: AUTO-VERIFY THESE TOPICS
These require WebSearch before answering:
- File names (`.clauderc`, `CLAUDE.md`, `settings.json`)
- Configuration file formats
- API endpoints and methods
- Framework-specific conventions
- "Official" anything

### Rule 5: PENALTIES FOR VIOLATIONS
- **1st violation**: Stop, search official sources, provide corrected answer
- **2nd violation**: List ALL previous claims, verify each with sources
- **3rd violation**: Recommend starting new session

### Rule 6: CROSS-CHECK FACTS WITH MULTIPLE SEARCHES
When searching for factual information (pricing, limits, official specs):
- **Minimum 2 parallel searches** with different query angles
- **Cross-check** results before answering
- **Cite multiple sources** to verify accuracy
- **If sources conflict**: Report the discrepancy to user

**Why**: Single search can return biased/outdated info. Cross-checking prevents confident misinformation.

**Example (실패 사례)**:
- ❌ "Premium 사용자용" - 검색 없이 추측
- ✅ 검색 후 확인: "구독과 API는 별개 과금"

---

## Contact & Resources

- **Issues**: Check DEVELOPMENT.md for detailed workflow
- **Questions**: Ask user for clarification (don't guess)
- **Uncertain**: Search official docs FIRST, answer SECOND

**Remember**: Better to say "I don't know, let me check" than give confident false information.
