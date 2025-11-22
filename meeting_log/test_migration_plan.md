# Test Migration Plan: Implementation → Behavior Testing

**Date:** 2025-11-22
**Goal:** Refactor from 90% Implementation Tests to 70% Behavior Tests (Chicago School TDD)
**Current:** 75 tests (70 pass on Mac, 5 skip)
**Target:** ~50 tests (fewer, but stronger)

---

## Current Test Analysis

### Test Distribution

```
Total: 75 tests
├── Unit Tests: 65 tests
│   ├── test_config.py: 29 tests
│   ├── test_notion_integration.py: 36 tests
│   ├── test_llm_processor.py: 2 tests
│   ├── test_utils.py: 1 test
│   ├── test_audio_processor.py: 2 tests (skip on Mac)
│   └── test_infrastructure.py: 2 tests (1 skip on Mac)
└── Integration Tests: 10 tests
    ├── test_gemini_connection.py: 1 test
    ├── test_audio.py: 1 test (skip on Mac)
    ├── test_gpu_precision.py: 1 test (skip on Mac)
    └── Manual scripts: 7 tests (not in pytest)
```

---

## Test Categorization

### Category 1: ✅ KEEP (Already Behavior-Focused)

**Tests that test WHAT, not HOW:**

1. **test_gemini_connection.py** (1 test)
   - `test_gemini_connection` - Tests real API connection
   - Status: ✅ Keep as-is
   - Reason: Already tests behavior (API connectivity)

2. **test_utils.py** (1 test)
   - `test_chunk_text` - Tests text chunking behavior
   - Status: ✅ Keep as-is
   - Reason: Tests public function behavior

**Total to Keep: 2 tests**

---

### Category 2: 🔄 REWRITE (Implementation → Behavior)

#### **test_notion_integration.py** (36 tests → 15 behavior tests)

**Current Issues:**
- ❌ Tests internal state (`assert client.page_id`)
- ❌ Tests method calls (`mock_client.assert_called_once_with`)
- ❌ Tests dictionary structure (`block["type"] == "heading_2"`)
- ❌ Heavy mocking (no real Notion API calls)

**Rewrite Strategy:**

| Old Test Class | Tests | New Behavior Test | Approach |
|----------------|-------|-------------------|----------|
| TestNotionClientInitialization | 3 | 1 behavior test | Test that client CAN create pages, not HOW it initializes |
| TestHeadingBlock | 3 | DELETE | Internal implementation detail |
| TestParagraphBlock | 3 | DELETE | Internal implementation detail |
| TestBulletedListBlock | 3 | DELETE | Internal implementation detail |
| TestTodoBlock | 3 | DELETE | Internal implementation detail |
| TestTextToBlocks | 6 | 3 behavior tests | Test final output format, not block creation |
| TestActionItemsToBlocks | 6 | 3 behavior tests | Test checkbox creation behavior |
| TestBuildBlocks | 2 | DELETE | Internal implementation |
| TestCreateMeetingMinutes | 5 | 5 behavior tests | **KEEP THESE** - test real page creation |
| TestKoreanTextHandling | 2 | 3 behavior tests | Test Korean in real Notion pages |

**New Behavior Tests:**

```python
# tests/behavior/test_notion_behavior.py

class TestNotionPageCreation:
    """Behavior: Creates meeting minutes page in Notion"""

    def test_creates_page_with_all_sections()
    def test_handles_long_text_over_2000_chars()
    def test_creates_action_items_as_checkboxes()
    def test_handles_korean_text_correctly()
    def test_returns_valid_notion_url()

class TestNotionContentFormatting:
    """Behavior: Formats content correctly in Notion"""

    def test_converts_bullet_lists()
    def test_creates_discussion_log_as_toggle()
    def test_handles_empty_sections()

class TestNotionErrorHandling:
    """Behavior: Handles errors gracefully"""

    def test_raises_error_when_api_key_invalid()
    def test_raises_error_when_page_id_invalid()
```

**Total: 36 implementation tests → 12 behavior tests**

---

#### **test_llm_processor.py** (2 tests → 8 behavior tests)

**Current Issues:**
- ❌ Tests mocked responses (`assert "This is a mock summary"`)
- ❌ Tests dictionary structure (`assert "summary" in result`)
- ❌ No real Gemini API testing

**New Behavior Tests:**

```python
# tests/behavior/test_llm_behavior.py

class TestMeetingMinutesGeneration:
    """Behavior: Generates meeting minutes from transcript"""

    @pytest.mark.integration
    def test_generates_summary_from_transcript()

    @pytest.mark.integration
    def test_includes_manual_notes_in_output()

    @pytest.mark.integration
    def test_identifies_action_items()

    @pytest.mark.integration
    def test_handles_korean_transcript()

    def test_raises_error_when_api_key_invalid()

class TestContentMerging:
    """Behavior: Merges transcript and manual notes"""

    @pytest.mark.integration
    def test_prioritizes_manual_notes_over_transcript()

    def test_handles_transcript_only()

    def test_handles_manual_notes_only()
```

**Total: 2 implementation tests → 8 behavior tests**

---

#### **test_config.py** (29 tests → 8 behavior tests)

**Current Issues:**
- ✅ Some tests are already behavior-focused (validation tests)
- ❌ Too many tests for internal details
- ❌ Tests implementation (type checks, value checks)

**Keep:**
- TestConfigValidation (6 tests) - ✅ Already behavior-focused

**Rewrite:**
- TestConfigEnvironmentVariables (4 → 1)
- TestConfigConstants (4 → DELETE, not important)
- TestConfigPaths (4 → 2)
- TestConfigSetupDirectories (3 → 2)
- TestConfigEdgeCases (5 → DELETE)
- TestConfigUsage (3 → DELETE)

**New Behavior Tests:**

```python
# tests/unit/test_config.py (simplified)

class TestConfigurationBehavior:
    """Behavior: Loads and validates configuration"""

    def test_validates_all_required_keys()
    def test_creates_upload_directory_when_missing()
    def test_loads_api_keys_from_environment()
    def test_provides_default_values_for_optional_settings()
```

**Total: 29 implementation tests → 8 behavior tests**

---

### Category 3: ❌ DELETE (Redundant or Not Needed)

1. **test_infrastructure.py** (2 tests)
   - Purpose: Test mock fixtures themselves
   - Action: DELETE - not testing actual code

2. **test_audio_processor.py** (2 tests)
   - Status: Skipped on Mac, implementation-focused
   - Action: Keep for Windows, but low priority

---

### Category 4: 🆕 CREATE (New Behavior Tests)

#### **E2E Workflow Tests**

```python
# tests/behavior/test_full_workflow_behavior.py

class TestEndToEndPipeline:
    """Behavior: Complete transcript to Notion workflow"""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_transcript_to_notion_full_pipeline()

    @pytest.mark.integration
    def test_handles_audio_transcription_to_notion()  # For Windows

    @pytest.mark.integration
    def test_merges_transcript_and_notes_to_notion()
```

**Total: 3 new E2E tests**

---

## Migration Summary

| Module | Current | Delete | Rewrite As | New | Total After |
|--------|---------|--------|------------|-----|-------------|
| **notion_integration** | 36 impl | 24 | 12 behavior | 0 | 12 |
| **llm_processor** | 2 impl | 2 | 8 behavior | 0 | 8 |
| **config** | 29 impl | 21 | 8 behavior | 0 | 8 |
| **utils** | 1 behavior | 0 | - | 0 | 1 ✅ |
| **gemini_connection** | 1 behavior | 0 | - | 0 | 1 ✅ |
| **infrastructure** | 2 mock | 2 | - | 0 | 0 |
| **E2E workflows** | 0 | 0 | - | 5 | 5 |
| **audio (Windows)** | 5 | 0 | TBD | 0 | 5 |
| **TOTAL** | **76** | **49** | **28** | **5** | **40** |

---

## Expected Outcomes

### Before (Current)
```
75 tests total
├── Implementation-focused: 90% (68 tests)
│   ├── Mock verification
│   ├── Internal state checks
│   └── Dictionary structure checks
├── Behavior-focused: 10% (7 tests)
└── Coverage: 70% (brittle)
```

### After (Target)
```
40 tests total
├── Behavior-focused: 70% (28 tests)
│   ├── Real API calls
│   ├── Public interface only
│   └── Observable outcomes
├── Integration tests: 25% (10 tests)
│   ├── E2E workflows
│   └── Real API integrations
├── Fast unit tests: 5% (2 tests)
│   └── Pure functions only
└── Coverage: 70%+ (more meaningful)
```

---

## Implementation Priority

### Phase 1: Foundation (Week 1)
1. ✅ Create `tests/helpers/` with API helpers
2. ✅ Update `tests/conftest.py` with behavior fixtures
3. ✅ Create `tests/behavior/` directory

### Phase 2: Core Modules (Week 1-2)
1. 🔄 Rewrite `test_notion_behavior.py` (12 tests)
2. 🔄 Rewrite `test_llm_behavior.py` (8 tests)
3. 🔄 Simplify `test_config.py` (8 tests)

### Phase 3: Integration (Week 2)
1. 🆕 Create `test_full_workflow_behavior.py` (5 tests)
2. 🆕 Automate E2E tests

### Phase 4: Cleanup (Week 2)
1. ❌ Delete old implementation tests
2. 📝 Update `DEVELOPMENT.md`
3. 📝 Update `README.md`

---

## Success Criteria

✅ **Tests pass:** All 40 behavior tests pass
✅ **Coverage:** 70%+ maintained
✅ **Refactoring safe:** Can change internal implementation without breaking tests
✅ **Real integration:** Notion and Gemini API tested with real calls
✅ **CI/CD ready:** All tests automated
✅ **Fast feedback:** Behavior tests complete in <30s

---

## Notes

- Keep old tests running in parallel during migration
- Delete old tests only after new behavior tests cover same functionality
- Use `@pytest.mark.integration` for tests requiring real APIs
- Use `@pytest.mark.slow` for tests taking >5s
- Create cleanup fixtures for Notion test pages

---

**Status:** Phase 0 Complete - Ready for Phase 1
