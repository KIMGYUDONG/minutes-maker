"""Test Notion integration without audio transcription or LLM."""

from notion_integration import NotionClient

# 테스트용 회의록 샘플 (실제 LLM 결과로 교체 가능)
sample_summary = """
신규 프로젝트 일정과 리소스 배정에 대한 회의를 진행했습니다.
기획안은 다음 주까지 완료 예정이며, 개발팀 3명이 다음 달 초부터 투입될 예정입니다.
"""

sample_key_updates = """
- 기획안 진행률: 80% 완료
- 다음 주까지 최종안 마무리 예정
- 개발팀 리소스: 3명 배정
- 투입 시기: 다음 달 초부터
"""

sample_discussion_log = """
- 신규 프로젝트 일정 논의
  - 김과장: 기획안 80% 완료, 다음 주까지 최종안 마무리 예정
  - 개발팀장: 다음 달 초부터 3명 투입 가능

- 리소스 배정 계획
  - 프론트엔드 개발자 2명
  - 백엔드 개발자 1명
  - 예상 개발 기간: 3개월

- 예산 및 일정 검토
  - 예산 승인 완료
  - 마일스톤 설정 필요
  - 주간 진행 상황 보고 필요
"""

sample_action_items = """
- [ ] 기획안 최종본 작성 및 공유 (김과장, 다음 주까지)
- [ ] 개발팀 투입 일정 확정 (개발팀장, 이번 주 금요일까지)
- [ ] 프로젝트 마일스톤 작성 (PM, 다음 주 월요일까지)
- [ ] 주간 보고 템플릿 준비 (PM, 이번 주 내)
- [ ] 킥오프 미팅 일정 잡기 (전체, 다음 달 첫째 주)
"""

def main():
    print("=== Notion Integration Test ===\n")

    try:
        # Notion Client 초기화
        print("1. Initializing Notion Client...")
        notion = NotionClient()
        print("✅ Notion Client initialized\n")

        # Notion 페이지 생성
        print("2. Creating Notion page...")
        url = notion.create_meeting_minutes(
            summary=sample_summary.strip(),
            key_updates=sample_key_updates.strip(),
            discussion_log=sample_discussion_log.strip(),
            action_items=sample_action_items.strip()
        )
        print(f"✅ Notion page created successfully!\n")

        # 결과 출력
        print("=" * 60)
        print("NOTION PAGE URL:")
        print("=" * 60)
        print(url)
        print()

        print("=" * 60)
        print("VERIFICATION:")
        print("=" * 60)
        print("1. Open the URL above in your browser")
        print("2. Check that the page has 4 sections:")
        print("   - 📝 Summary")
        print("   - 🔑 Key Updates")
        print("   - 💬 Discussion Log (in toggle block)")
        print("   - ✅ Action Items (as checkboxes)")
        print("3. Verify the content matches the sample data")
        print()

        print("✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
