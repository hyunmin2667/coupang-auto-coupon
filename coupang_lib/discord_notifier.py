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
    
def send_discord_success_notification(message: str, subject: str = "스크립트 성공 알림"):
    """
    Discord 웹훅을 통해 성공 알림 메시지를 전송합니다.
    기본 subject는 '스크립트 성공 알림'입니다.
    """
    return send_discord_notification(message, subject)

def send_discord_failure_notification(message: str, subject: str = "스크립트 실패 알림"):
    """
    Discord 웹훅을 통해 실패 알림 메시지를 전송합니다.
    메시지 내용에는 자동으로 '@everyone' 멘션이 추가됩니다.
    기본 subject는 '스크립트 실패 알림'입니다.
    """
    # 실패 알림에 @everyone 멘션 추가
    full_message = f"@everyone \n{message}"
    return send_discord_notification(full_message, subject)


# 테스트용 코드 (직접 실행 시)
if __name__ == '__main__':
    print("--- Discord 알림 테스트 시작 ---")

    # 1. 일반 알림 테스트
    print("\n[테스트 1/3] 일반 알림 전송 시도...")
    test_message_general = "이것은 일반 Discord 알림 테스트 메시지입니다."
    send_discord_notification(test_message_general, "테스트 일반 알림")

    # 2. 성공 알림 테스트
    print("\n[테스트 2/3] 성공 알림 전송 시도...")
    test_message_success = "스크립트 실행이 성공적으로 완료되었습니다!"
    send_discord_success_notification(test_message_success)

    # 3. 실패 알림 테스트
    print("\n[테스트 3/3] 실패 알림 전송 시도 (콘솔에 @everyone 포함 메시지 보일 것)...")
    test_message_failure = "중요한 스크립트 실행 중 오류가 발생했습니다. 즉시 확인해주세요!"
    send_discord_failure_notification(test_message_failure)

    print("\n--- Discord 알림 테스트 완료 ---")