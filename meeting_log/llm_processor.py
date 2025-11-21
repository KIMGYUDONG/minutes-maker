"""LLM processing module using Google Gemini Pro."""

import google.generativeai as genai
from typing import Optional
from datetime import datetime
from config import Config


class LLMProcessor:
    """Handles meeting minutes generation using Gemini Pro."""
    
    def __init__(self):
        """Initialize the Gemini Pro client."""
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] LLMProcessor.__init__() 시작")
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")

        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] Gemini API 설정 중...")
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] 모델명: {Config.GEMINI_MODEL_NAME}")
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.GEMINI_MODEL_NAME)
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] Gemini 모델 초기화 완료")
    
    def create_meeting_minutes(
        self,
        transcript: str,
        manual_notes: Optional[str] = None
    ) -> dict:
        """
        Generate structured meeting minutes from transcript and manual notes.
        
        Args:
            transcript: Audio transcript from Whisper
            manual_notes: Optional manual notes provided by user
            
        Returns:
            Dictionary with summary, key_updates, discussion_log, and action_items
        """
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] create_meeting_minutes() 시작")
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] Transcript 길이: {len(transcript)} 글자")
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] Manual notes: {len(manual_notes) if manual_notes else 0} 글자")

        prompt = self._build_prompt(transcript, manual_notes)
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] Prompt 생성 완료: {len(prompt)} 글자")

        try:
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] ⏳ Gemini API 호출 중... (응답 대기)")
            start_time = datetime.now()

            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more focused output
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] ✅ Gemini API 응답 수신 (소요시간: {elapsed:.2f}초)")
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] 응답 텍스트 길이: {len(response.text)} 글자")

            result = self._parse_response(response.text)
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] 응답 파싱 완료")
            return result
            
        except Exception as e:
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] ❌ Gemini API 호출 실패!")
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] 에러 타입: {type(e).__name__}")
            print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] 에러 메시지: {str(e)}")
            raise RuntimeError(f"Failed to generate meeting minutes: {str(e)}")
    
    def _build_prompt(self, transcript: str, manual_notes: Optional[str]) -> str:
        """
        Build the prompt for Gemini Pro.
        
        Args:
            transcript: Audio transcript
            manual_notes: Optional manual notes
            
        Returns:
            Formatted prompt string
        """
        prompt = """You are an expert meeting minutes assistant for a Korean team. Your task is to create comprehensive, well-structured meeting minutes in Korean.

You will receive:
1. **Audio Transcript**: Automatically transcribed speech from the meeting
2. **Manual Notes**: Hand-written notes provided by the user (may be empty)

**IMPORTANT INSTRUCTIONS:**
- If manual notes are provided, treat them as the AUTHORITATIVE source
- Use the transcript to enrich details and provide context
- If there's a conflict, prioritize the manual notes
- Merge both sources intelligently to create comprehensive minutes
- Write in clear, professional Korean
- Focus on actionable insights and decisions
- Use the hierarchical numbering format: 1. → a. → •

**OUTPUT FORMAT:**
Structure your response EXACTLY as follows with Korean section headers:

## 요약
[2-3 문장으로 회의 전체 내용을 간단히 요약]

## 업데이트
[중요한 업데이트, 결정사항, 공지사항을 계층적으로 구조화]
1. **주요 업데이트 제목**
    a. 세부 사항 1
        • 상세 내용 또는 설명
        • 추가 정보
    b. 세부 사항 2
        • 상세 내용
2. **두 번째 업데이트**
    a. 세부 사항
        • 내용

## 논의사항
[회의에서 논의된 주요 주제와 의견을 구조화]
1. **논의 주제 1**
    a. 참석자 의견 또는 관점
        • 구체적인 논점
        • 추가 논의 내용
    b. 결론 또는 합의사항
2. **논의 주제 2**
    • 주요 논점

## 할 일
[담당자별 액션 아이템을 명확하게 기술]
1. **담당자 이름:**
    • 구체적인 할 일 1
    • 구체적인 할 일 2
2. **다른 담당자:**
    • 할 일

**STRUCTURE RULES:**
- Use "1.", "2.", "3." for main points
- Use "a.", "b.", "c." for sub-points (indented under numbers)
- Use "•" for detailed items (indented under letters)
- Keep formatting consistent throughout

---

**AUDIO TRANSCRIPT:**
```
{transcript}
```

**MANUAL NOTES:**
```
{manual_notes}
```

Now generate the meeting minutes following the exact format above:"""
        
        return prompt.format(
            transcript=transcript if transcript else "No transcript available",
            manual_notes=manual_notes if manual_notes else "No manual notes provided"
        )
    
    def _parse_response(self, response_text: str) -> dict:
        """
        Parse the LLM response into structured sections.
        
        Args:
            response_text: Raw response from Gemini Pro
            
        Returns:
            Dictionary with sections
        """
        sections = {
            "summary": "",
            "key_updates": "",
            "discussion_log": "",
            "action_items": "",
            "raw_output": response_text
        }

        lines = response_text.split('\n')
        current_section = None
        section_content = []

        for line in lines:
            line_lower = line.lower().strip()

            # 요약 섹션 감지
            if '요약' in line or 'summary' in line_lower:
                if line.startswith('#'):
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content).strip()
                    current_section = "summary"
                    section_content = []
                    continue

            # 업데이트 섹션 감지
            if '업데이트' in line or 'updates' in line_lower or 'key updates' in line_lower:
                if line.startswith('#'):
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content).strip()
                    current_section = "key_updates"
                    section_content = []
                    continue

            # 논의사항 섹션 감지
            if '논의사항' in line or 'discussion' in line_lower:
                if line.startswith('#'):
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content).strip()
                    current_section = "discussion_log"
                    section_content = []
                    continue

            # 할 일 섹션 감지
            if '할 일' in line or '할일' in line or 'action' in line_lower:
                if line.startswith('#'):
                    if current_section and section_content:
                        sections[current_section] = '\n'.join(section_content).strip()
                    current_section = "action_items"
                    section_content = []
                    continue

            # 섹션 헤더가 아니면 내용 추가
            if current_section and line.strip() and not line.startswith('##'):
                section_content.append(line)

        # Handle the final section after loop ends
        if current_section and section_content:
            sections[current_section] = '\n'.join(section_content).strip()
        
        return sections
