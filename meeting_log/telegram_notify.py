"""Telegram notification module for meeting minutes."""

import os
import requests
from typing import Optional


def send_telegram_notification(notion_url: str) -> bool:
    """노션 저장 완료 알림을 텔레그램으로 전송.

    Args:
        notion_url: 저장된 노션 페이지 URL

    Returns:
        bool: 전송 성공 여부
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[WARN] Telegram credentials not configured, skipping notification")
        return False

    message = (
        "✅ 회의록 저장 완료\n"
        f"📎 {notion_url}"
    )

    # 인라인 키보드 버튼 (맥북 텔레그램 데스크탑에서 클릭 시 URL 스킴 호출)
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "🚀 Linear 이슈 등록",
                "url": "https://kimgyudong.github.io/minutes-maker/runlinear.html"
            }
        ]]
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "reply_markup": keyboard
        }, timeout=10)

        if response.ok:
            print(f"[INFO] Telegram notification sent successfully")
            return True
        else:
            print(f"[ERROR] Telegram API error: {response.text}")
            return False

    except requests.RequestException as e:
        print(f"[ERROR] Failed to send Telegram notification: {e}")
        return False


def send_telegram_notification_to_user(
    user_name: str, notion_url: str, client_name: str
) -> bool:
    """Send Telegram notification to a specific user.

    Args:
        user_name: User identifier (key in Config.TELEGRAM_USERS)
        notion_url: Notion page URL
        client_name: Client company name

    Returns:
        bool: True if sent successfully
    """
    from config import Config

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = Config.TELEGRAM_USERS.get(user_name)

    if not bot_token or not chat_id:
        print(f"[WARN] Telegram not configured for user '{user_name}', skipping")
        return False

    message = (
        f"📋 숨고 클라이언트 회의록 생성 완료\n\n"
        f"클라이언트: {client_name}\n"
        f"담당자: {user_name}\n\n"
        f"📎 {notion_url}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
        }, timeout=10)
        if response.ok:
            print(f"[INFO] Telegram notification sent to {user_name}")
            return True
        else:
            print(f"[ERROR] Telegram API error for {user_name}: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Failed to send Telegram to {user_name}: {e}")
        return False
