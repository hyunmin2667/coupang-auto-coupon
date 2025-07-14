# coupang_lib/discord_notifier.py

import requests
import os

def send_discord_notification(message: str, subject: str = "자동화 스크립트 알림"):
    """
    Discord 웹훅을 통해 메시지를 전송합니다.
    웹훅 URL은 환경 변수 'DISCORD_WEBHOOK_URL'에서 가져옵니다.
    """
    WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    if not WEBHOOK_URL:
        print("[경고] Discord 웹훅 URL 환경 변수(DISCORD_WEBHOOK_URL)가 설정되지 않았습니다. 알림을 보낼 수 없습니다.")
        return False

    # Discord에 보낼 JSON 데이터 구성
    # content: 메시지 내용
    # username: 웹훅 메시지의 발신자 이름 (선택 사항)
    # avatar_url: 웹훅 메시지의 프로필 사진 URL (선택 사항)
    # embeds: 더 구조화된 메시지를 보내고 싶을 때 사용 (선택 사항)
    payload = {
        "username": "스크립트 실행 알림",
        "content": f"**[{subject}]**\n{message}" # 제목을 메시지 내용에 포함
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload)
        response.raise_for_status() # HTTP 오류(4xx, 5xx)가 발생하면 예외 발생
        print(f"성공: Discord 알림 전송 완료. 상태 코드: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[오류] Discord 알림 전송 실패: {e}")
        return False

# 테스트용 코드 (직접 실행 시)
if __name__ == '__main__':
    test_message = "이것은 Discord 알림 테스트 메시지입니다. 스크립트가 성공적으로 Discord 알림을 보낼 수 있는지 확인합니다."
    send_discord_notification(test_message, "테스트 알림 @everyone")