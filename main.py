# main.py

import time
import schedule
from typing import Callable, Any
import traceback # 상세한 오류 정보를 얻기 위해 추가

from coupang_lib.config import VENDOR_ID, COUPON_CYCLE_MINUTES, API_GATEWAY_URL, ACCESS_KEY, SECRET_KEY
from coupang_lib.api_client import CoupangApiClient
from coupang_lib.coupang_api_utils import create_new_coupon_util, check_coupon_status_util, apply_coupon_to_items_util, get_active_coupons_by_keyword, deactivate_coupon
from coupang_lib.item_loader import load_vendor_items_from_csv
from coupang_lib.logger import logger
from coupang_lib.discord_notifier import send_discord_notification


# --- 설정 가능한 상수 정의 (config.config.py로 이동을 고려) ---
MAX_DEACTIVATION_RETRIES = 3
MAX_STATUS_POLLING_ATTEMPTS = 10
STATUS_POLLING_INTERVAL_SEC = 5
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


# --- 새로운 제네릭 폴링 헬퍼 함수 ---
def _poll_status_for_requested_id(
    api_client_instance: CoupangApiClient,
    vendor_id: str,
    requested_id: str,
    max_attempts: int,
    sleep_interval_sec: int
) -> Any | None:
    """
    requestedId에 대해 특정 상태가 될 때까지 API를 폴링합니다.
    성공 시 해당 결과(예: couponId)를 반환하고, 실패 시 None을 반환합니다.
    """
    for attempt in range(max_attempts):
        logger.info(f"요청 ID {requested_id} 상태 확인 중... (시도 {attempt + 1}/{max_attempts})")
        # check_coupon_status_util은 DONE이면 coupon_id 반환, 아니면 None (FAIL, REQUESTED 포함)
        poll_result = check_coupon_status_util(api_client_instance, vendor_id, requested_id)
        
        if poll_result is not None: # DONE 상태 (coupon_id가 반환됨)
            return poll_result
        
        logger.debug(f"요청 ID {requested_id} 상태 아직 완료되지 않음. {sleep_interval_sec}초 후 재시도...")
        time.sleep(sleep_interval_sec)
        
    logger.warning(f"[경고] 요청 ID {requested_id}가 지정된 {max_attempts}회 시도 내에 완료되지 않았습니다.")
    return None


def get_and_deactivate_auto_coupons_request(api_client_instance: CoupangApiClient, vendor_id: str) -> bool:
    """
    API를 사용하여 활성화된 "자동쿠폰_" 쿠폰을 조회하고 모두 파기(비활성화)합니다.
    개별 비활성화 요청 후 그 상태를 폴링합니다.
    """
    logger.info("[쿠폰 자동화] API로 기존 '자동쿠폰_' 쿠폰 비활성화 프로세스 시작...")

    coupons_to_deactivate = get_active_coupons_by_keyword(api_client_instance, vendor_id, "자동쿠폰_")

    if coupons_to_deactivate is None: # <-- 조회 자체에 실패한 경우 (None 반환)
        logger.error("[실패] 활성 쿠폰 목록 조회 중 치명적인 오류가 발생하여 비활성화 프로세스를 진행할 수 없습니다.")
        return False # <-- 명확히 실패로 처리

    if not coupons_to_deactivate: # <-- 조회는 성공했으나 비활성화할 쿠폰이 없는 경우 (빈 리스트 반환)
        logger.info("API로 비활성화할 '자동쿠폰_' 쿠폰이 없습니다.")
        return True # <-- 이 경우는 성공으로 처리

    logger.info(f"API로 비활성화할 '자동쿠폰_' 쿠폰 {len(coupons_to_deactivate)}개 발견.")

    successfully_deactivated_count = 0
    total_coupons_to_deactivate = len(coupons_to_deactivate)

    for coupon in coupons_to_deactivate:
        # ... (기존 비활성화 로직 유지) ...
        coupon_id = coupon.get('couponId')
        accurate_coupon_name = coupon.get('promotionName', '이름 없음')

        if not coupon_id:
            logger.warning(f"[실패] 쿠폰 비활성화 시도 실패: 쿠폰 ID를 찾을 수 없음 (이름: {accurate_coupon_name}).")
            continue

        # 비활성화 요청
        logger.info(f"쿠폰 {coupon_id} 비활성화 요청 중... (이름: '{accurate_coupon_name}')")
        deactivation_requested_id = deactivate_coupon(api_client_instance, vendor_id, coupon_id, accurate_coupon_name)

        if not deactivation_requested_id:
            logger.warning(f"[실패] 쿠폰 {coupon_id} 비활성화 요청 실패 또는 Requested ID를 받지 못했습니다.")
            # 비활성화 요청 자체에 실패했으므로 카운트하지 않고 다음 쿠폰으로 이동
            # 이 경우 total_coupons_to_deactivate와 successfully_deactivated_count가 달라져 최종 False 반환에 기여
            continue

        # 비활성화 상태 폴링
        poll_result = _poll_status_for_requested_id(
            api_client_instance,
            vendor_id,
            deactivation_requested_id,
            MAX_STATUS_POLLING_ATTEMPTS,
            STATUS_POLLING_INTERVAL_SEC
        )

        if poll_result is not None: # DONE 상태 (coupon_id가 반환됨)
            successfully_deactivated_count += 1
            logger.info(f"[성공] 쿠폰 {coupon_id} 비활성화 요청 ({deactivation_requested_id}) 완료.")
        else:
            logger.warning(f"[경고] 쿠폰 {coupon_id} 비활성화 요청 ({deactivation_requested_id})이 지정된 시간 내에 완료되지 않았거나 실패했습니다.")

    logger.info(f"API로 총 {total_coupons_to_deactivate}개 '자동쿠폰_' 쿠폰 중 {successfully_deactivated_count}개 비활성화 완료.")
    # 모든 쿠폰이 성공적으로 비활성화 요청되고, 그 상태 확인까지 완료되었는지 여부
    return successfully_deactivated_count == total_coupons_to_deactivate

# --- 리팩토링된 메인 사이클 헬퍼 함수들 ---

def _handle_deactivation_phase(api_client_instance: CoupangApiClient, vendor_id: str) -> bool:
    """
    기존 자동 생성 쿠폰을 비활성화하는 단계를 처리합니다.
    재시도 로직을 포함합니다.
    """
    for attempt in range(MAX_DEACTIVATION_RETRIES):
        logger.info(f"기존 쿠폰 비활성화 시도 중... (시도 {attempt + 1}/{MAX_DEACTIVATION_RETRIES})")
        # get_and_deactivate_auto_coupons_request 함수가 이제 내부에서 개별 쿠폰의 폴링까지 처리
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
    requested_id = create_coupon_request() # 래퍼 함수 호출
    if not requested_id:
        logger.error("쿠폰 생성 요청 실패.")
        return None

    logger.info(f"쿠폰 생성 요청 완료. Requested ID: {requested_id}")
    time.sleep(STATUS_POLLING_INTERVAL_SEC * 2) # 쿠폰 생성 후 서버 반영을 위한 대기 (기존 2초 유지)
    logger.info(f"쿠폰 생성 후 {STATUS_POLLING_INTERVAL_SEC * 2}초 대기 중...")

    # 쿠폰 생성 상태 폴링 (제네릭 헬퍼 함수 사용)
    coupon_id = _poll_status_for_requested_id(
        api_client_instance, 
        vendor_id, 
        requested_id, 
        MAX_STATUS_POLLING_ATTEMPTS, 
        STATUS_POLLING_INTERVAL_SEC
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
        apply_requested_id = apply_coupon_to_items_request(coupon_id) # 래퍼 함수 호출
        
        if apply_requested_id:
            # 쿠폰 적용 요청 상태 폴링 (제네릭 헬퍼 함수 사용)
            poll_result = _poll_status_for_requested_id(
                api_client_instance, 
                VENDOR_ID, # VENDOR_ID는 main.py의 전역 또는 config에서 가져옴
                apply_requested_id, 
                MAX_STATUS_POLLING_ATTEMPTS, 
                STATUS_POLLING_INTERVAL_SEC
            )
            
            if poll_result is not None: # DONE 상태 (coupon_id가 반환됨)
                logger.info("[성공] 쿠폰 적용 완료!")
                return True
            else:
                logger.warning(f"[경고] 쿠폰 {coupon_id} 품목 적용 요청 ({apply_requested_id})이 지정된 시간 내에 완료되지 않았거나 실패했습니다.")
        else:
            logger.warning(f"[실패] 쿠폰 {coupon_id} 품목 적용 요청 실패 또는 Requested ID를 받지 못했습니다.")

        if (attempt_apply + 1) < MAX_APPLY_RETRIES: # 아직 성공 못했고 재시도 기회가 남았다면
            logger.warning(f"[실패] 쿠폰 {coupon_id} 품목 적용 실패 (시도 {attempt_apply + 1}/{MAX_APPLY_RETRIES}). {APPLY_RETRY_DELAY_SEC}초 후 재시도...")
            time.sleep(APPLY_RETRY_DELAY_SEC) # 재시도 전 딜레이
    
    logger.error(f"[오류] 쿠폰 {coupon_id} 품목 적용이 반복 실패하여 다음 사이클까지 기다립니다.")
    return False # 최종 적용 실패


# 메인 쿠폰 자동화 사이클 함수
def run_coupon_cycle():
    """
    쿠폰 자동화의 전체 사이클을 실행합니다.
    기존 자동 생성 쿠폰 비활성화, 새 쿠폰 생성, 상태 확인 및 품목 적용을 포함합니다.
    최종 성공 또는 실패 여부를 Discord 알림으로 보냅니다.
    """
    logger.info("\n--- 쿠폰 자동화: 새로운 쿠폰 갱신 사이클 시작 ---")
    cycle_success = True  # 사이클 전체 성공 여부 플래그
    notification_message = ""
    notification_subject = "쿠폰 자동화 스크립트 알림"

    try:
        if not VENDOR_ITEMS:
            notification_message = "[경고] VENDOR_ITEMS가 로드되지 않아 쿠폰 생성 및 적용을 건너뜁니다."
            logger.warning(notification_message)
            cycle_success = False
            return # 함수 종료 (finally 블록에서 알림 처리)

        # 1. 기존 쿠폰 비활성화 단계 처리
        if not _handle_deactivation_phase(api_client, VENDOR_ID):
            notification_message = "[오류] 기존 쿠폰 비활성화 단계 실패. 다음 단계로 진행하지 않습니다."
            logger.error(notification_message)
            cycle_success = False
            return

        # 2. 새 쿠폰 생성 및 상태 확인 단계 처리
        coupon_id = _create_and_poll_coupon(api_client, VENDOR_ID)
        if not coupon_id:
            notification_message = "[오류] 새 쿠폰 생성 단계 실패. 다음 단계로 진행하지 않습니다."
            logger.error(notification_message)
            cycle_success = False
            return

        # 쿠폰 상태 반영 후 적용 전 대기
        time.sleep(STATUS_POLLING_INTERVAL_SEC)
        logger.info(f"쿠폰 상태 확인 후 {STATUS_POLLING_INTERVAL_SEC}초 대기 중...")

        # 3. 쿠폰 품목 적용 단계 처리
        if not _apply_coupon_with_retries(api_client, coupon_id, VENDOR_ITEMS):
            notification_message = "[오류] 쿠폰 품목 적용 단계 실패."
            logger.error(notification_message)
            cycle_success = False
            return

        # 모든 단계 성공 시
        notification_message = "쿠폰 자동화 사이클이 성공적으로 완료되었습니다."
        logger.info("--- 쿠폰 자동화: 쿠폰 갱신 사이클 종료 (성공) ---")
        cycle_success = True # 명시적으로 성공 상태 설정

    except Exception as e:
        # 예상치 못한 다른 모든 오류 처리
        error_details = traceback.format_exc()
        notification_message = f"[치명적 오류] 쿠폰 자동화 사이클 실행 중 예상치 못한 오류 발생: {e}\n\n상세 정보:\n```{error_details}```"
        notification_subject = "긴급 알림: 쿠폰 자동화 스크립트 치명적 오류"
        logger.critical(notification_message)
        cycle_success = False

    finally:
        # 최종 성공/실패 여부에 따라 Discord 알림 전송
        if cycle_success:
            send_discord_notification(notification_message, f"{notification_subject} (성공)")
        else:
            send_discord_notification(notification_message, f"{notification_subject} (실패) @everyone")


# 자동 실행 설정
if __name__ == "__main__":
    logger.info(f"쿠폰 자동화 시작: {COUPON_CYCLE_MINUTES}분마다 쿠폰 갱신 실행 대기 중")

    run_coupon_cycle() # 최초 1회 실행

    schedule.every(COUPON_CYCLE_MINUTES).minutes.do(run_coupon_cycle)

    while True:
        schedule.run_pending()
        time.sleep(10)