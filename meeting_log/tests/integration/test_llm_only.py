"""Test LLM processor without audio transcription."""

from llm_processor import LLMProcessor

# 테스트용 전사본 (실제 전사 결과로 교체 가능)
test_transcript = """
안녕하세요. 오늘 회의를 시작하겠습니다.
첫 번째 안건은 신규 프로젝트 일정에 대한 논의입니다.
김과장님, 현재 진행 상황을 공유해주시겠습니까?
네, 현재 기획안이 80% 완료되었고, 다음 주까지 최종안을 마무리할 예정입니다.
좋습니다. 개발팀은 언제부터 투입 가능한가요?
다음 달 초부터 가능합니다. 리소스는 3명 배정 예정입니다.
알겠습니다. 그럼 다음 액션 아이템을 정리하겠습니다.
"""

# 테스트용 수동 메모 (선택사항)
test_manual_notes = """
- 신규 프로젝트 일정 논의
- 기획안 다음 주까지 완료
- 개발팀 3명 투입
"""

def main():
    print("=== LLM Processor Test ===\n")

    try:
        # LLM Processor 초기화
        print("1. Initializing LLM Processor...")
        llm = LLMProcessor()
        print("✅ LLM Processor initialized\n")

        # 회의록 생성
        print("2. Generating meeting minutes...")
        minutes = llm.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=test_manual_notes
        )
        print("✅ Meeting minutes generated\n")

        # 결과 출력
        print("=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print(minutes['summary'])
        print()

        print("=" * 60)
        print("KEY UPDATES:")
        print("=" * 60)
        print(minutes['key_updates'])
        print()

        print("=" * 60)
        print("DISCUSSION LOG:")
        print("=" * 60)
        print(minutes['discussion_log'])
        print()

        print("=" * 60)
        print("ACTION ITEMS:")
        print("=" * 60)
        print(minutes['action_items'])
        print()

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
