import datetime
import time
import schedule
from typing import Callable, Any, Tuple
import traceback

from coupang_lib.config import VENDOR_ID, COUPON_CYCLE_MINUTES, API_GATEWAY_URL, ACCESS_KEY, SECRET_KEY
from coupang_lib.api_client import CoupangApiClient
from coupang_lib.coupang_api_utils import create_new_coupon_util, check_coupon_status_util, apply_coupon_to_items_util, get_active_coupons_by_keyword, deactivate_coupon
from coupang_lib.item_loader import load_vendor_items_from_csv
from coupang_lib.logger import logger
from coupang_lib.discord_notifier import send_discord_success_notification, send_discord_failure_notification


# --- 설정 가능한 상수 정의 (config.config.py로 이동을 고려) ---
MAX_DEACTIVATION_RETRIES = 3
MAX_APPLY_RETRIES = 3
APPLY_RETRY_DELAY_SEC = 5
# ----------------------------------------------------


# API 클라이언트 인스턴스 초기화
api_client = CoupangApiClient(ACCESS_KEY, SECRET_KEY, API_GATEWAY_URL)

# 판매자 품목 데이터 로드
VENDOR_ITEMS = load_vendor_items_from_csv()


# --- 핵심 API 유틸리티 함수를 감싸는 래퍼 함수들 ---
def create_coupon_request():
    """새로운 쿠폰 생성 요청을 수행합니다."""
    return create_new_coupon_util(api_client, VENDOR_ID)


def check_requested_status(requested_id):
    """요청 ID에 대한 상태를 확인하고, 완료되면 쿠폰 ID를 반환합니다."""
    return check_coupon_status_util(api_client, VENDOR_ID, requested_id)


def apply_coupon_to_items_request(coupon_id):
    """생성된 쿠폰을 로드된 품목에 적용 요청합니다. (Requested ID 반환)"""
    return apply_coupon_to_items_util(api_client, VENDOR_ID, coupon_id, VENDOR_ITEMS)


# 최대 폴링 시간 (초) 및 경고 임계값 설정
MAX_POLLING_TIME_SEC = 3600  # 총 1시간 (60분)까지 폴링 시도
NOTIFICATION_THRESHOLD_SEC = 900 # 15분 (900초) 이상 지연 시 경고 로깅


def _poll_status_for_requested_id(
    api_client_instance: CoupangApiClient,
    vendor_id: str,
    requested_id: str
) -> int | None:
    """
    requestedId에 대해 특정 상태가 될 때까지 API를 폴링합니다.
    총 폴링 시간에 따라 대기 간격을 점진적으로 늘립니다.
    성공적으로 'DONE' 상태가 되면 해당 couponId (int)를 반환하고,
    그 외의 경우 (FAIL, ERROR, 또는 최대 폴링 시간 초과) None을 반환합니다.
    """
    start_time = time.monotonic()
    attempt = 0
    total_elapsed_time_sec = 0
    
    # 알림이 이미 한 번 발생했는지 추적하는 플래그
    notification_sent = False 

    while total_elapsed_time_sec < MAX_POLLING_TIME_SEC:
        attempt += 1
        
        # 현재까지 경과된 시간에 따라 동적으로 대기 간격 결정
        if total_elapsed_time_sec < 60: # 1분 미만: 5초 단위
            sleep_interval_sec = 5
        elif total_elapsed_time_sec < 5 * 60: # 1분 이상 5분 미만: 30초 단위
            sleep_interval_sec = 30
        elif total_elapsed_time_sec < 30 * 60: # 5분 이상 30분 미만: 1분 단위 (60초)
            sleep_interval_sec = 60
        else: # 30분 이상: 5분 단위 (300초)
            sleep_interval_sec = 300 
        
        logger.info(f"요청 ID {requested_id} 상태 확인 중... (시도 {attempt}, 경과 시간: {total_elapsed_time_sec:.0f}초, 다음 대기: {sleep_interval_sec}초)")
        
        status, coupon_id = check_coupon_status_util(api_client_instance, vendor_id, requested_id)
        
        if status == "DONE":
            logger.info(f"요청 ID {requested_id} 처리 완료. 쿠폰 ID: {coupon_id}")
            return coupon_id
        elif status == "FAIL" or status == "ERROR":
            logger.error(f"요청 ID {requested_id} 처리 실패 또는 오류 발생. 폴링 중단.")
            return None
        
        # REQUESTED 상태일 경우 대기 후 재시도
        total_elapsed_time_sec = time.monotonic() - start_time
        
        # 특정 시간 이상 지연될 경우 상세 알림 로깅 및 Discord 알림 전송 (한 번만)
        if total_elapsed_time_sec >= NOTIFICATION_THRESHOLD_SEC and not notification_sent:
            alert_message = (
                f"요청 ID '{requested_id}'의 쿠폰 처리가 "
                f"{total_elapsed_time_sec:.0f}초 ({total_elapsed_time_sec / 60:.1f}분) 이상 지연 중입니다. "
                "수동 확인이 필요할 수 있습니다."
            )
            logger.warning(f"[쿠폰 처리 지연 알림] {alert_message}")
            send_discord_failure_notification(alert_message, "긴급 알림: 쿠폰 처리 지연")
            notification_sent = True
            
        # MAX_POLLING_TIME_SEC에 도달하기 전에만 sleep
        # 다음 대기 후에도 MAX_POLLING_TIME_SEC를 초과하지 않을 경우에만 sleep
        if total_elapsed_time_sec + sleep_interval_sec < MAX_POLLING_TIME_SEC:
            logger.debug(f"요청 ID {requested_id} 상태 아직 완료되지 않음 ({status}). {sleep_interval_sec}초 후 재시도...")
            time.sleep(sleep_interval_sec)
        else:
            # 최대 시간 초과 직전 또는 초과 후에는 더 이상 대기하지 않고 루프를 종료
            break # 루프를 빠져나와 최종 실패 메시지로 이동

    # while 루프가 종료될 경우 (MAX_POLLING_TIME_SEC 초과했거나 break에 의해)
    # 이때만 최종 실패 알림을 보냅니다.
    alert_message = (
        f"요청 ID '{requested_id}'의 쿠폰 처리가 "
        f"지정된 최대 폴링 시간 ({MAX_POLLING_TIME_SEC}초, 약 {MAX_POLLING_TIME_SEC / 60:.0f}분) 내에 완료되지 않았습니다. 폴링을 중단합니다."
    )
    logger.warning(f"[쿠폰 처리 시간 초과] {alert_message}")
    send_discord_failure_notification(alert_message, "긴급 알림: 쿠폰 처리 시간 초과")
    return None



def get_and_deactivate_auto_coupons_request(api_client_instance: CoupangApiClient, vendor_id: str) -> bool:
    """
    API를 사용하여 활성화된 "자동쿠폰_" 쿠폰을 조회하고 모두 파기(비활성화)합니다.
    개별 비활성화 요청 후 그 상태를 폴링합니다.
    """
    logger.info("[쿠폰 자동화] API로 기존 '자동쿠폰_' 쿠폰 비활성화 프로세스 시작...")

    coupons_to_deactivate = get_active_coupons_by_keyword(api_client_instance, vendor_id, "자동쿠폰_")

    if coupons_to_deactivate is None:
        logger.error("[실패] 활성 쿠폰 목록 조회 중 치명적인 오류가 발생하여 비활성화 프로세스를 진행할 수 없습니다.")
        return False

    if not coupons_to_deactivate:
        logger.info("API로 비활성화할 '자동쿠폰_' 쿠폰이 없습니다.")
        return True

    logger.info(f"API로 비활성화할 '자동쿠폰_' 쿠폰 {len(coupons_to_deactivate)}개 발견.")

    successfully_deactivated_count = 0
    total_coupons_to_deactivate = len(coupons_to_deactivate)

    for coupon in coupons_to_deactivate:
        coupon_id = coupon.get('couponId')
        accurate_coupon_name = coupon.get('promotionName', '이름 없음')

        if not coupon_id:
            logger.warning(f"[실패] 쿠폰 비활성화 시도 실패: 쿠폰 ID를 찾을 수 없음 (이름: {accurate_coupon_name}).")
            continue

        logger.info(f"쿠폰 {coupon_id} 비활성화 요청 중... (이름: '{accurate_coupon_name}')")
        deactivation_requested_id = deactivate_coupon(api_client_instance, vendor_id, coupon_id, accurate_coupon_name)

        if not deactivation_requested_id:
            logger.warning(f"[실패] 쿠폰 {coupon_id} 비활성화 요청 실패 또는 Requested ID를 받지 못했습니다.")
            continue

        poll_result = _poll_status_for_requested_id(
            api_client_instance,
            vendor_id,
            deactivation_requested_id
        )

        if poll_result is not None:
            successfully_deactivated_count += 1
            logger.info(f"[성공] 쿠폰 {coupon_id} 비활성화 요청 ({deactivation_requested_id}) 완료.")
        else:
            logger.warning(f"[경고] 쿠폰 {coupon_id} 비활성화 요청 ({deactivation_requested_id})이 지정된 시간 내에 완료되지 않았거나 실패했습니다.")

    logger.info(f"API로 총 {total_coupons_to_deactivate}개 '자동쿠폰_' 쿠폰 중 {successfully_deactivated_count}개 비활성화 완료.")
    return successfully_deactivated_count == total_coupons_to_deactivate


def _handle_deactivation_phase(api_client_instance: CoupangApiClient, vendor_id: str) -> bool:
    """
    기존 자동 생성 쿠폰을 비활성화하는 단계를 처리합니다.
    재시도 로직을 포함합니다.
    """
    for attempt in range(MAX_DEACTIVATION_RETRIES):
        logger.info(f"기존 쿠폰 비활성화 시도 중... (시도 {attempt + 1}/{MAX_DEACTIVATION_RETRIES})")
        if get_and_deactivate_auto_coupons_request(api_client_instance, vendor_id):
            logger.info("[성공] 기존 쿠폰 비활성화 프로세스 완료.")
            return True
        else:
            logger.warning(f"[실패] 기존 쿠폰 비활성화 실패 (시도 {attempt + 1}/{MAX_DEACTIVATION_RETRIES}). {APPLY_RETRY_DELAY_SEC}초 후 재시도...")
            time.sleep(APPLY_RETRY_DELAY_SEC)
    logger.error("[오류] 기존 쿠폰 비활성화가 반복 실패하여 다음 단계로 진행하지 않습니다.")
    return False

def _create_and_poll_coupon(api_client_instance: CoupangApiClient, vendor_id: str) -> int | None:
    """
    새로운 쿠폰을 생성하고, 생성 완료 상태를 폴링하여 쿠폰 ID를 반환합니다.
    """
    requested_id = create_coupon_request()
    if not requested_id:
        logger.error("쿠폰 생성 요청 실패.")
        return None

    logger.info(f"쿠폰 생성 요청 완료. Requested ID: {requested_id}")
    time.sleep(5)
    logger.info(f"쿠폰 생성 후 5초 대기 중...")

    coupon_id = _poll_status_for_requested_id(
        api_client_instance, 
        vendor_id, 
        requested_id
    )
    
    if coupon_id is None:
        logger.warning("[경고] 지정된 시간 내에 쿠폰 생성이 완료되지 않았습니다.")
    return coupon_id


def _apply_coupon_with_retries(api_client_instance: CoupangApiClient, coupon_id: int, vendor_items: list) -> bool:
    """
    생성된 쿠폰을 품목에 적용합니다. 재시도 로직을 포함합니다.
    """
    for attempt_apply in range(MAX_APPLY_RETRIES):
        logger.info(f"쿠폰 {coupon_id} 품목 적용 시도 중... (시도 {attempt_apply + 1}/{MAX_APPLY_RETRIES})")
        apply_requested_id = apply_coupon_to_items_request(coupon_id)
        
        if apply_requested_id:
            poll_result = _poll_status_for_requested_id(
                api_client_instance, 
                VENDOR_ID, 
                apply_requested_id
            )
            
            if poll_result is not None:
                logger.info("[성공] 쿠폰 적용 완료!")
                return True
            else:
                logger.warning(f"[경고] 쿠폰 {coupon_id} 품목 적용 요청 ({apply_requested_id})이 지정된 시간 내에 완료되지 않았거나 실패했습니다.")
        else:
            logger.warning(f"[실패] 쿠폰 {coupon_id} 품목 적용 요청 실패 또는 Requested ID를 받지 못했습니다.")

        if (attempt_apply + 1) < MAX_APPLY_RETRIES:
            logger.warning(f"[실패] 쿠폰 {coupon_id} 품목 적용 실패 (시도 {attempt_apply + 1}/{MAX_APPLY_RETRIES}). {APPLY_RETRY_DELAY_SEC}초 후 재시도...")
            time.sleep(APPLY_RETRY_DELAY_SEC)
    
    logger.error(f"[오류] 쿠폰 {coupon_id} 품목 적용이 반복 실패하여 다음 사이클까지 기다립니다.")
    return False


# 메인 쿠폰 자동화 사이클 함수
def run_coupon_cycle():
    """
    쿠폰 자동화의 전체 사이클을 실행합니다.
    기존 자동 생성 쿠폰 비활성화, 새 쿠폰 생성, 상태 확인 및 품목 적용을 포함합니다.
    최종 성공 또는 실패 여부를 Discord 알림으로 보냅니다.
    """
    logger.info("\n--- 쿠폰 자동화: 새로운 쿠폰 갱신 사이클 시작 ---")
    
    notification_message = ""
    notification_subject_prefix = "쿠폰 자동화 스크립트" # 제목 접두사

    try:
        if not VENDOR_ITEMS:
            notification_message = "[경고] VENDOR_ITEMS가 로드되지 않아 쿠폰 생성 및 적용을 건너뜁니다."
            logger.warning(notification_message)
            send_discord_failure_notification(notification_message, f"{notification_subject_prefix} (실패)")
            return 

        if not _handle_deactivation_phase(api_client, VENDOR_ID):
            notification_message = "[오류] 기존 쿠폰 비활성화 단계 실패. 다음 단계로 진행하지 않습니다."
            logger.error(notification_message)
            send_discord_failure_notification(notification_message, f"{notification_subject_prefix} (실패)")
            return

        coupon_id = _create_and_poll_coupon(api_client, VENDOR_ID)
        if not coupon_id:
            notification_message = "[오류] 새 쿠폰 생성 단계 실패. 다음 단계로 진행하지 않습니다."
            logger.error(notification_message)
            send_discord_failure_notification(notification_message, f"{notification_subject_prefix} (실패)")
            return

        time.sleep(5)
        logger.info(f"쿠폰 상태 확인 후 5초 대기 중...")

        if not _apply_coupon_with_retries(api_client, coupon_id, VENDOR_ITEMS):
            notification_message = "[오류] 쿠폰 품목 적용 단계 실패."
            logger.error(notification_message)
            send_discord_failure_notification(notification_message, f"{notification_subject_prefix} (실패)")
            return
        
        next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=COUPON_CYCLE_MINUTES)
        next_run_time_str = next_run_time.strftime('%Y년 %m월 %d일 %H시 %M분')

        notification_message = f"쿠폰 자동화 사이클이 성공적으로 완료되었습니다. 다음 실행 예정: {next_run_time_str}"

        logger.info(notification_message)
        logger.info("--- 쿠폰 자동화: 쿠폰 갱신 사이클 종료 (성공) ---")
        send_discord_success_notification(notification_message, f"{notification_subject_prefix} (성공)")

    except Exception as e:
        error_details = traceback.format_exc()
        notification_message = f"[치명적 오류] 쿠폰 자동화 사이클 실행 중 예상치 못한 오류 발생: {e}\n\n상세 정보:\n```{error_details}```"
        critical_subject = f"긴급 알림: {notification_subject_prefix} 치명적 오류"
        logger.critical(notification_message)
        send_discord_failure_notification(notification_message, critical_subject)


# 자동 실행 설정
if __name__ == "__main__":
    logger.info(f"쿠폰 자동화 시작: {COUPON_CYCLE_MINUTES}분마다 쿠폰 갱신 실행 대기 중")

    run_coupon_cycle() # 최초 1회 실행

    schedule.every(COUPON_CYCLE_MINUTES).minutes.do(run_coupon_cycle)

    while True:
        schedule.run_pending()
        time.sleep(10)