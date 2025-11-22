"""Test complete workflow: Transcript → LLM → Notion (without audio)."""

from llm_processor import LLMProcessor
from notion_integration import NotionClient

# 테스트용 전사본
test_transcript = """
안녕하세요. 오늘 회의를 시작하겠습니다.
첫 번째 안건은 신규 프로젝트 일정에 대한 논의입니다.
김과장님, 현재 진행 상황을 공유해주시겠습니까?
네, 현재 기획안이 80% 완료되었고, 다음 주까지 최종안을 마무리할 예정입니다.
좋습니다. 개발팀은 언제부터 투입 가능한가요?
다음 달 초부터 가능합니다. 리소스는 3명 배정 예정입니다.
알겠습니다. 그럼 다음 액션 아이템을 정리하겠습니다.
기획안 최종본 작성, 개발팀 투입 일정 확정, 마일스톤 작성이 필요합니다.
다음 주 월요일까지 킥오프 미팅 일정을 잡도록 하겠습니다.
"""

# 테스트용 수동 메모
test_manual_notes = """
- 신규 프로젝트 일정 논의
- 기획안 다음 주까지 완료
- 개발팀 3명 투입
- 킥오프 미팅 예정
"""

def main():
    print("=" * 80)
    print("=== FULL WORKFLOW TEST: Transcript → LLM → Notion ===")
    print("=" * 80)
    print()

    try:
        # Step 1: LLM으로 회의록 생성
        print("STEP 1: Generate Meeting Minutes with LLM")
        print("-" * 80)
        print("1-1. Initializing LLM Processor...")
        llm = LLMProcessor()
        print("     ✅ LLM Processor initialized")

        print("1-2. Generating meeting minutes from transcript...")
        minutes = llm.create_meeting_minutes(
            transcript=test_transcript,
            manual_notes=test_manual_notes
        )
        print("     ✅ Meeting minutes generated")
        print()

        # 중간 결과 출력
        print("     📄 Generated Sections:")
        print(f"        - Summary: {len(minutes['summary'])} chars")
        print(f"        - Key Updates: {len(minutes['key_updates'])} chars")
        print(f"        - Discussion Log: {len(minutes['discussion_log'])} chars")
        print(f"        - Action Items: {len(minutes['action_items'])} chars")
        print()

        # Step 2: Notion에 업로드
        print("STEP 2: Export to Notion")
        print("-" * 80)
        print("2-1. Initializing Notion Client...")
        notion = NotionClient()
        print("     ✅ Notion Client initialized")

        print("2-2. Creating Notion page...")
        url = notion.create_meeting_minutes(
            summary=minutes['summary'],
            key_updates=minutes['key_updates'],
            discussion_log=minutes['discussion_log'],
            action_items=minutes['action_items']
        )
        print("     ✅ Notion page created successfully!")
        print()

        # 최종 결과
        print("=" * 80)
        print("✅ FULL WORKFLOW COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print(f"📝 Notion Page URL: {url}")
        print()
        print("🔍 Verification Steps:")
        print("   1. Open the URL above in your browser")
        print("   2. Verify the page has proper structure")
        print("   3. Check all 4 sections are present and formatted correctly")
        print("   4. Verify action items are checkboxes")
        print()

        # 상세 결과 출력 (선택)
        print_detailed = input("Print detailed meeting minutes? (y/n): ").lower() == 'y'
        if print_detailed:
            print()
            print("=" * 80)
            print("DETAILED MEETING MINUTES:")
            print("=" * 80)
            print()
            print("📝 SUMMARY:")
            print("-" * 80)
            print(minutes['summary'])
            print()
            print("🔑 KEY UPDATES:")
            print("-" * 80)
            print(minutes['key_updates'])
            print()
            print("💬 DISCUSSION LOG:")
            print("-" * 80)
            print(minutes['discussion_log'])
            print()
            print("✅ ACTION ITEMS:")
            print("-" * 80)
            print(minutes['action_items'])
            print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR OCCURRED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
