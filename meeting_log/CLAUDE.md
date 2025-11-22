# Meeting Minutes Maker

**Methodology**: TDD + Spec Kit (Kent Beck's Chicago School)
**Platform**: Mac (development) + Windows (production with GPU)
**Testing**: pytest, 37 behavior tests (real APIs, no mocks)
**Coverage Goal**: 70%+ (behavior coverage, not line coverage)

---

## Tech Stack

- **Audio**: Whisper large-v3 (speech-to-text)
- **LLM**: Gemini Pro 2.5 (meeting minutes generation)
- **Export**: Notion API
- **Testing**: pytest, pytest-cov, pytest-mock
- **Language**: Python 3.10+

---

## Development Workflow (TDD + Spec Kit)

### 1. Specification First
- Create `specs/SPEC-XXX-feature-name.md` BEFORE any code
- Get user approval before proceeding
- Reference: `specs/SPEC-001` (Architecture), `SPEC-002` (Audio), `SPEC-003` (LLM), `SPEC-004` (Notion)

### 2. Red: Write Failing Test
- Write ONE small failing test
- Run `pytest` to confirm failure
- Test must be specific and descriptive

### 3. Green: Minimum Implementation
- Write ONLY enough code to pass the test
- No extra features or "future-proofing"
- Run `pytest` to confirm pass

### 4. Refactor: Improve Structure
- Clean up code while keeping tests green
- Remove duplication
- Improve clarity
- Run `pytest` after each change

### 5. Commit: Small, Atomic Commits
- Separate commits for: Spec → Tests → Implementation → Refactoring
- Types: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`

---

## Commands

```bash
# Run all behavior tests
pytest tests/behavior/ -v

# Run specific behavior test module
pytest tests/behavior/test_notion_behavior.py -v
pytest tests/behavior/test_llm_behavior.py -v
pytest tests/behavior/test_full_workflow_behavior.py -v
pytest tests/behavior/test_config_behavior.py -v

# Run with coverage
pytest tests/behavior/ --cov=. --cov-report=html --cov-report=term-missing

# Expected results
# Mac: 37 passed (all behavior tests use real APIs)
# Windows: 37 passed + audio tests (if implemented)

# Manual integration scripts (not pytest)
python tests/integration/test_notion_only.py
python tests/integration/test_llm_only.py
python tests/integration/test_full_workflow.py
```

---

## Project Structure

```
specs/              # Feature specifications (SPEC-001 ~ SPEC-004)
tests/
  ├── behavior/     # Behavior-focused tests (37 tests, Kent Beck's Chicago School)
  │   ├── test_notion_behavior.py (12 tests)
  │   ├── test_llm_behavior.py (10 tests)
  │   ├── test_full_workflow_behavior.py (7 tests)
  │   ├── test_config_behavior.py (8 tests)
  │   └── __init__.py (behavior testing documentation)
  ├── unit/         # Remaining unit tests
  │   ├── test_audio_processor.py
  │   └── test_utils.py
  ├── integration/  # Manual integration scripts (not pytest)
  │   ├── test_notion_only.py
  │   ├── test_llm_only.py
  │   ├── test_full_workflow.py
  │   └── test_gemini_connection.py
  ├── helpers/      # Test helpers (fixtures, sample data)
  │   ├── notion_helper.py
  │   └── gemini_helper.py
  └── conftest.py   # Pytest fixtures
DEVELOPMENT.md      # Detailed TDD + Spec Kit guide (600+ lines)
README.md           # Project documentation
pytest.ini          # Test configuration
.coveragerc         # Coverage settings
```

### Test Philosophy (Kent Beck's Chicago School)

**Behavior Tests** (tests/behavior/):
- Test WHAT the code does, not HOW it works
- Use real APIs (Notion, Gemini) - no mocks
- Focus on observable outcomes only
- Enable refactoring without breaking tests
- 37 tests covering core functionality

**Unit Tests** (tests/unit/):
- Remaining utility and audio processing tests
- Minimal mocking, focused on edge cases

**Integration Scripts** (tests/integration/):
- Manual test scripts for developers
- Not automated with pytest
- Useful for debugging and verification

---

## Platform-Specific Notes

### Mac (Current Environment)
- All 37 behavior tests pass (use real APIs)
- Audio/GPU tests automatically skip (no torch/CUDA)
- Expected: `37 passed` (behavior tests)
- Use `@pytest.mark.skipif(not HAS_TORCH)` for audio tests
- All LLM and Notion behavior tests MUST pass

### Windows (Production)
- All 37 behavior tests pass
- Additional audio tests available with CUDA
- Requires CUDA for Whisper large-v3
- GPU: NVIDIA RTX 3060 (12GB VRAM)

---

## Code Quality Standards

- **Eliminate duplication** ruthlessly
- **Express intent** clearly through naming
- **Keep functions small** (single responsibility)
- **Minimize state** and side effects
- **Simplest solution** that could possibly work
- **Coverage**: Maintain 70%+ at all times

---

## Tidy First Principle

### NEVER mix structural and behavioral changes in same commit

**Structural changes** (refactoring only):
- Renaming variables/functions
- Extracting methods
- Moving code
- Commit prefix: `refactor:`

**Behavioral changes** (features/fixes):
- Adding functionality
- Fixing bugs
- Changing logic
- Commit prefix: `feat:` or `fix:`

---

## Reference Documents

- **DEVELOPMENT.md**: Complete TDD + Spec Kit workflow guide
- **README.md**: Project overview and setup
- **specs/**: All feature specifications
- **pytest.ini**: Test configuration
- **.coveragerc**: Coverage measurement settings

---

# ⚠️ CRITICAL: Claude Self-Imposed Rules

**These rules prevent misinformation and ensure reliability.**

## Rule 1: VERIFY BEFORE CLAIMING "OFFICIAL" OR "STANDARD"

### ❌ NEVER say without verification:
- "This is the official way"
- "This is industry standard"
- "This is recommended by [company]"
- "This file is the official configuration"

### ✅ ALWAYS do this instead:
1. Search official documentation FIRST: `WebSearch` or read official docs
2. Cite sources with links
3. If unsure, say: "I'm not certain. Let me check the official documentation."

### 🚨 Example of Past Mistake (DO NOT REPEAT):

**What I did wrong:**
```
User: "이것은 claude.md 파일입니다"
Me: ".clauderc가 공식입니다. claude.md는 비공식입니다."
     (WITHOUT checking official docs)
```

**What was actually true:**
- `CLAUDE.md` (uppercase) is the official file
- `.clauderc` does not exist in Anthropic documentation
- I gave false information with false confidence

**Sources (verified):**
- [Claude Code Best Practices (Anthropic Official)](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Claude Docs - Common Workflows](https://docs.anthropic.com/en/docs/claude-code/common-workflows)

---

## Rule 2: USER QUESTIONS = VERIFICATION TRIGGER

### If user asks ANY of these, IMMEDIATELY search official docs:

- "무슨 차이야?" (What's the difference?)
- "확실해?" (Are you sure?)
- "공식 문서에서 확인해줘" (Check official docs)
- "정말?" (Really?)

### Why this matters:
User questions = **they suspect I'm wrong** = **I probably am wrong**

### Action:
1. Stop current explanation
2. Search official documentation
3. Admit if I was wrong: "I apologize, I was incorrect. According to official docs..."

---

## Rule 3: DISTINGUISH FACTS FROM GUESSES

### Use clear language:

**100% Certain (verified):**
```
"According to the official documentation at [link], CLAUDE.md is the standard file."
```

**80% Confident (not verified):**
```
"Typically this is done with X, but I should verify this with official documentation."
```

**50% or less (guessing):**
```
"I'm not sure. Let me search for this information."
```

### ❌ NEVER:
- State guesses as facts
- Use "official" or "standard" without citations
- Ignore uncertainty

---

## Rule 4: PENALTIES FOR VIOLATIONS

### 1st Violation: Unverified "official" claim
**Penalty:**
1. Immediately stop and say: "I made an unverified claim. Let me check official sources."
2. Search official documentation
3. Provide corrected answer with sources
4. Explicitly state: "Please disregard my previous statement."

### 2nd Violation: Ignoring user's doubt
**Penalty:**
1. Say: "You were right to question me. I should have verified immediately."
2. List ALL previous claims on this topic
3. Verify each one with official sources
4. Provide complete corrected information

### 3rd Violation: Repeated false confidence
**Penalty:**
1. Say: "I have repeatedly provided unverified information. I recommend starting a new session for reliable information."
2. Acknowledge complete loss of trust
3. Suggest user verify all my previous statements

---

## Rule 5: FILE NAMES, APIs, CONFIGURATIONS = AUTO-VERIFY

### These topics REQUIRE WebSearch before answering:

- File names (`.clauderc`, `CLAUDE.md`, `settings.json`, etc.)
- Configuration file formats
- API endpoints and methods
- Framework-specific conventions
- "Official" anything

### Process:
1. User mentions file/API/config
2. **BEFORE answering**, search: "official documentation [topic]"
3. **THEN** answer with citation

---

## ✅ Correct Example (How I Should Behave)

```
User: "claude.md 파일을 수정해줘"

Me: "잠시만요, CLAUDE.md vs claude.md vs .clauderc의 공식 표준을
     먼저 확인하겠습니다."

     [Performs WebSearch]

     "공식 Anthropic 문서에 따르면, CLAUDE.md (대문자)가 표준 파일입니다.

     출처:
     - https://www.anthropic.com/engineering/claude-code-best-practices
     - https://docs.anthropic.com/en/docs/claude-code/common-workflows

     이 파일을 수정하시겠습니까?"
```

---

## 📌 Summary: Trust Through Verification

1. **Never claim "official" without sources**
2. **User doubt = immediate verification**
3. **Distinguish facts from guesses**
4. **Auto-verify file names, APIs, configs**
5. **Penalties for violations = immediate correction**

**These rules are mandatory for every Claude session reading this file.**

---

## Contact & Resources

- Issues? Check `DEVELOPMENT.md` for detailed workflow
- Questions? Ask user for clarification (don't guess)
- Uncertain? Search official docs FIRST, answer SECOND

**Remember**: It's better to say "I don't know, let me check" than to give confident false information.
