# 개발 가이드 (Development Guide)

**Meeting Minutes Generator** 프로젝트 개발 가이드입니다.

---

## 📋 목차

1. [개발 환경 설정](#개발-환경-설정)
2. [TDD + Spec Kit 워크플로우](#tdd--spec-kit-워크플로우)
3. [테스트 실행](#테스트-실행)
4. [Mac vs Windows 환경 차이](#mac-vs-windows-환경-차이)
5. [새 기능 추가 프로세스](#새-기능-추가-프로세스)
6. [코드 품질 도구](#코드-품질-도구)

---

## 개발 환경 설정

### 1. 프로젝트 클론

```bash
git clone <repository-url>
cd meeting_log
```

### 2. 가상 환경 설정

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows
```

### 3. 의존성 설치

**프로덕션 의존성:**
```bash
pip install -r requirements.txt
```

**개발 의존성 (테스트, 린터 등):**
```bash
pip install -r requirements-dev.txt
```

### 4. 환경 변수 설정

`.env` 파일 생성:
```bash
cp .env.example .env
```

필수 환경 변수 설정:
```env
GEMINI_API_KEY=<your_gemini_api_key>
NOTION_TOKEN=<your_notion_integration_token>
NOTION_PAGE_ID=<your_notion_database_id>
```

---

## TDD + Spec Kit 워크플로우

이 프로젝트는 **Spec-Driven Development** + **Test-Driven Development** 방법론을 사용합니다.

### 전체 개발 사이클

```
1. Spec Kit (명세서) → 2. TDD (테스트) → 3. Implementation (구현) → 4. Refactor
```

### 1️⃣ Spec Kit: 명세서 작성

새 기능을 추가하기 전에 명세서를 작성합니다.

**명세서 위치**: `specs/SPEC-XXX-feature-name.md`

**명세서 템플릿**:
```markdown
# SPEC-XXX: [Feature Name]

**Status**: Draft / In Progress / Implemented
**Version**: 1.0
**Last Updated**: YYYY-MM-DD
**Dependencies**: SPEC-001, SPEC-002

## Overview
[간단한 기능 설명]

## Requirements

### Functional Requirements
- FR-001: [요구사항]
- FR-002: [요구사항]

### Non-Functional Requirements
- NFR-001: [성능/보안 요구사항]

## Architecture
[시스템 구조도, 클래스 다이어그램 등]

## Detailed Specifications
[상세 스펙: 메서드, 파라미터, 리턴 값, 예외 처리 등]

## Testing Strategy
[테스트 전략: Unit, Integration, Edge Cases]

## References
[관련 문서 링크]
```

**예시**: `specs/SPEC-004-notion-integration.md` 참고

### 2️⃣ TDD: 테스트 먼저 작성 (Red)

명세서를 기반으로 테스트를 먼저 작성합니다.

**테스트 파일 위치**:
- Unit 테스트: `tests/unit/test_<module_name>.py`
- Integration 테스트: `tests/integration/test_<feature>.py`

**테스트 작성 원칙**:
```python
class TestFeatureName:
    """Test [feature description]."""

    @pytest.fixture
    def client(self):
        """Fixture for test setup."""
        # Setup code
        yield client
        # Teardown code (optional)

    def test_success_case(self, client):
        """Test successful operation."""
        # Arrange
        input_data = "test"

        # Act
        result = client.method(input_data)

        # Assert
        assert result == expected_value

    def test_error_handling(self, client):
        """Test error handling."""
        with pytest.raises(ValueError, match="error message"):
            client.method(invalid_input)
```

**테스트 실행 (Red 확인)**:
```bash
pytest tests/unit/test_new_feature.py -v
```
→ 아직 구현 안 했으니 실패해야 정상!

### 3️⃣ Implementation: 구현 (Green)

테스트를 통과하도록 최소한의 코드를 작성합니다.

```python
# new_feature.py
class NewFeature:
    """Implement the new feature."""

    def method(self, input_data: str) -> str:
        # 테스트를 통과하도록 구현
        return expected_value
```

**테스트 실행 (Green 확인)**:
```bash
pytest tests/unit/test_new_feature.py -v
```
→ 모든 테스트 통과!

### 4️⃣ Refactor: 리팩토링

테스트를 통과하면서 코드를 개선합니다.

```python
# 코드 개선: 가독성, 성능, 중복 제거 등
def method(self, input_data: str) -> str:
    """Improved documentation."""
    # 더 명확한 변수명
    validated_input = self._validate(input_data)
    # 중복 제거
    return self._process(validated_input)
```

**테스트 재실행 (여전히 통과하는지 확인)**:
```bash
pytest tests/unit/test_new_feature.py -v
```

---

## 테스트 실행

### 전체 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 디렉토리만 실행
pytest tests/unit -v
pytest tests/integration -v
```

### Mac 환경 (Audio 테스트 스킵)

Mac에서는 Whisper/Torch가 설치되지 않으므로 audio 관련 테스트가 자동으로 스킵됩니다.

```bash
# Mac에서 실행 (audio 테스트 자동 스킵)
pytest tests/ -v

# 결과:
# ✅ 70 passed
# ⏭️  5 skipped (torch not available)
```

### Windows 환경 (전체 테스트)

Windows Desktop에서는 모든 테스트를 실행할 수 있습니다.

```bash
# Windows에서 실행 (GPU/Audio 테스트 포함)
pytest tests/ -v

# 결과:
# ✅ 75 passed (모든 테스트)
```

### 커버리지 리포트 생성

```bash
# HTML 리포트 생성
pytest --cov=. --cov-report=html --cov-report=term-missing

# 리포트 확인
open htmlcov/index.html  # Mac
start htmlcov\index.html  # Windows
```

**현재 커버리지**:
- `notion_integration.py`: 96.36%
- `llm_processor.py`: 88.17%
- `utils.py`: 50.94%
- **Overall (audio 제외)**: ~70%

### 특정 테스트만 실행

```bash
# 특정 파일 테스트
pytest tests/unit/test_notion_integration.py -v

# 특정 클래스 테스트
pytest tests/unit/test_notion_integration.py::TestHeadingBlock -v

# 특정 테스트 함수
pytest tests/unit/test_notion_integration.py::TestHeadingBlock::test_heading_level_2 -v

# 마커로 필터링
pytest -m "not gpu" -v  # GPU 테스트 제외
```

---

## Mac vs Windows 환경 차이

### 개발 환경 분리

| 환경 | 역할 | 특징 |
|------|------|------|
| **Mac (Client)** | 코드 편집, Git Push | Whisper/GPU 없음, LLM/Notion 테스트만 |
| **Windows Desktop (Server)** | Streamlit 실행, GPU 사용 | 전체 기능 실행 가능 |

### Mac 환경 제약사항

**설치되지 않는 패키지**:
- `torch` / `torchaudio` - Python 3.14 호환성 문제
- `openai-whisper` - torch 의존성

**자동 스킵되는 테스트**:
- `tests/integration/test_audio.py` - 오디오 로딩 테스트
- `tests/integration/test_gpu_precision.py` - GPU 정밀도 테스트
- `tests/unit/test_audio_processor.py` - Audio Processor 유닛 테스트
- `tests/unit/test_infrastructure.py::test_whisper_mock` - Whisper Mock 테스트

### 스킵 메커니즘

**조건부 스킵 구현** (`conftest.py`):
```python
# torch 가용성 확인
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# 테스트 파일에서 사용
pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch not available (Mac environment)")
```

### 워크플로우

**Mac에서 개발 → Windows에서 실행**:
```bash
# 1. Mac에서 코드 작성 및 커밋
git add .
git commit -m "feat: New feature"
git push origin main

# 2. Windows에서 Pull 및 실행
git pull origin main
streamlit run app.py
```

---

## 새 기능 추가 프로세스

### 예시: "화자 분리 (Speaker Diarization)" 기능 추가

#### Step 1: 명세서 작성

```bash
# 명세서 파일 생성
touch specs/SPEC-005-speaker-diarization.md
```

`SPEC-005-speaker-diarization.md` 내용:
```markdown
# SPEC-005: 화자 분리 (Speaker Diarization)

## Overview
오디오 파일에서 여러 화자를 구분하여 각 발화를 화자별로 라벨링합니다.

## Requirements
- FR-001: 화자별로 transcript 분리
- FR-002: 화자 수 자동 감지 또는 수동 입력
- FR-003: 회의록에 화자 정보 포함

## Architecture
- `SpeakerDiarizer` 클래스 생성
- Whisper + pyannote.audio 통합

## Testing Strategy
- Unit: 화자 분리 로직
- Integration: 실제 오디오 파일 테스트
```

#### Step 2: 테스트 작성 (Red)

```bash
# 테스트 파일 생성
touch tests/unit/test_speaker_diarizer.py
```

```python
# tests/unit/test_speaker_diarizer.py
import pytest
from speaker_diarizer import SpeakerDiarizer

class TestSpeakerDiarizer:
    """Test speaker diarization functionality."""

    @pytest.fixture
    def diarizer(self):
        return SpeakerDiarizer()

    def test_detect_speakers(self, diarizer):
        """Test detecting number of speakers."""
        # 이 시점에서 SpeakerDiarizer는 아직 존재하지 않음!
        audio_path = "test_audio.wav"
        result = diarizer.detect_speakers(audio_path)

        assert result["num_speakers"] >= 1
        assert "segments" in result

    def test_assign_speaker_labels(self, diarizer):
        """Test assigning speaker labels to segments."""
        segments = [
            {"start": 0, "end": 5, "text": "Hello"},
            {"start": 6, "end": 10, "text": "World"}
        ]

        labeled = diarizer.assign_labels(segments)

        assert labeled[0]["speaker"] == "Speaker 1"
```

**테스트 실행 (실패 확인)**:
```bash
pytest tests/unit/test_speaker_diarizer.py -v
# ❌ ModuleNotFoundError: No module named 'speaker_diarizer'
```

#### Step 3: 구현 (Green)

```bash
# 모듈 파일 생성
touch speaker_diarizer.py
```

```python
# speaker_diarizer.py
from typing import List, Dict, Any

class SpeakerDiarizer:
    """Handles speaker diarization for audio files."""

    def detect_speakers(self, audio_path: str) -> Dict[str, Any]:
        """Detect number of speakers and their segments."""
        # 최소 구현 (테스트 통과용)
        return {
            "num_speakers": 1,
            "segments": []
        }

    def assign_labels(self, segments: List[Dict]) -> List[Dict]:
        """Assign speaker labels to segments."""
        labeled = []
        for segment in segments:
            segment["speaker"] = "Speaker 1"
            labeled.append(segment)
        return labeled
```

**테스트 실행 (통과 확인)**:
```bash
pytest tests/unit/test_speaker_diarizer.py -v
# ✅ 2 passed
```

#### Step 4: 리팩토링

```python
# speaker_diarizer.py (개선 버전)
from typing import List, Dict, Any
import torch
from pyannote.audio import Pipeline

class SpeakerDiarizer:
    """Handles speaker diarization using pyannote.audio."""

    def __init__(self):
        self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

    def detect_speakers(self, audio_path: str) -> Dict[str, Any]:
        """Detect speakers using pyannote.audio."""
        diarization = self.pipeline(audio_path)

        segments = []
        speakers = set()

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            })
            speakers.add(speaker)

        return {
            "num_speakers": len(speakers),
            "segments": segments
        }

    def assign_labels(self, segments: List[Dict]) -> List[Dict]:
        """Assign human-readable labels to speakers."""
        # 실제 화자 매핑 로직
        speaker_map = {}
        label_counter = 1

        for segment in segments:
            speaker_id = segment.get("speaker")
            if speaker_id and speaker_id not in speaker_map:
                speaker_map[speaker_id] = f"Speaker {label_counter}"
                label_counter += 1

            segment["speaker"] = speaker_map.get(speaker_id, "Unknown")

        return segments
```

**테스트 재실행 (여전히 통과하는지 확인)**:
```bash
pytest tests/unit/test_speaker_diarizer.py -v
# ✅ 2 passed (Mock으로 pyannote bypass)
```

#### Step 5: 통합 및 커밋

```bash
# 전체 테스트 실행
pytest tests/ -v

# 커버리지 확인
pytest --cov=. --cov-report=term-missing

# 커밋
git add .
git commit -m "feat: 화자 분리 (Speaker Diarization) 기능 추가"
```

---

## 코드 품질 도구

### 1. Black (코드 포맷터)

**설치**: `requirements-dev.txt`에 포함됨

**실행**:
```bash
# 전체 프로젝트 포맷
black .

# 특정 파일만
black speaker_diarizer.py

# Dry-run (변경사항 미리보기)
black --check .
```

### 2. Flake8 (린터)

**실행**:
```bash
# 전체 프로젝트 검사
flake8 .

# 특정 파일만
flake8 speaker_diarizer.py
```

### 3. MyPy (타입 체커)

**실행**:
```bash
# 타입 검사
mypy .

# 특정 파일만
mypy speaker_diarizer.py
```

### 4. isort (Import 정렬)

**실행**:
```bash
# Import 문 정렬
isort .

# 특정 파일만
isort speaker_diarizer.py
```

### Pre-commit Hook (권장)

모든 커밋 전에 자동으로 코드 품질 검사:

```bash
# .git/hooks/pre-commit 생성
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
black --check .
flake8 .
pytest tests/ -q
EOF

chmod +x .git/hooks/pre-commit
```

---

## 참고 자료

### 프로젝트 문서
- [README.md](README.md) - 프로젝트 개요 및 사용법
- [TESTING.md](TESTING.md) - 테스트 전략 상세 설명
- [specs/](specs/) - 기술 명세서 디렉토리

### 외부 문서
- [Spec Kit Documentation](https://github.com/github/spec-kit)
- [pytest Documentation](https://docs.pytest.org/)
- [Test-Driven Development by Example](https://www.oreilly.com/library/view/test-driven-development/0321146530/)

---

## 문의 및 기여

문제가 발생하거나 기여하고 싶으시면:
- GitHub Issues: [링크]
- Pull Request 환영합니다!

**개발 규칙**:
1. ✅ 테스트 먼저 작성 (TDD)
2. ✅ 명세서 기반 개발 (Spec-Driven)
3. ✅ 커밋 전 테스트 통과 확인
4. ✅ 코드 리뷰 후 Merge
