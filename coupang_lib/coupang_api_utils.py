from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

from coupang_lib.logger import logger
from coupang_lib.api_client import CoupangApiClient
from coupang_lib.config import VENDOR_ID, CONTRACT_ID, COUPON_DISCOUNT_RATE, COUPON_MAX_DISCOUNT_PRICE, COUPON_CYCLE_MINUTES


def get_active_coupons_by_keyword(api: CoupangApiClient, vendor_id: str, keyword: str) -> List[Dict[str, Any]] | None:
    """
    현재 활성화된 쿠폰 목록을 조회하고, 특정 키워드로 필터링하여 반환합니다.
    API 호출 중 오류 발생 시 None을 반환합니다.
    """
    logger.info(f"[API 조회] 활성 쿠폰 목록 (키워드: '{keyword}') 조회 시도 중...")

    query_params = {
        "status": "APPLIED",
        "page": 1,
        "size": 100,
        "sort": "desc"
    }

    try:
        res = api.get(f"/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupons", query_params)

        if res.get('code') == 200 and res.get('data') and res['data'].get('content'):
            all_active_coupons = res['data']['content']
            filtered_coupons = [
                c for c in all_active_coupons
                if c.get('promotionName') and keyword in c['promotionName']
            ]
            logger.info(f"[성공] 활성 쿠폰 목록 조회 성공. '{keyword}' 포함 쿠폰 {len(filtered_coupons)}개 발견.")
            return filtered_coupons
        else:
            logger.warning(f"[실패] 활성 쿠폰 목록 조회 실패: {res.get('message', '알 수 없는 오류')}")
            return []
    except Exception as e:
        logger.error(f"[실패] 활성 쿠폰 목록 조회 중 오류 발생: {e}", exc_info=True)
        return None


def deactivate_coupon(api: CoupangApiClient, vendor_id: str, coupon_id: int, coupon_name: str = "알 수 없는 쿠폰") -> str | None:
    """
    API를 사용하여 특정 쿠폰을 파기(비활성화)하고, 요청 ID를 반환합니다.
    """
    logger.info(f"[API 파기] 쿠폰 {coupon_id} 비활성화 시도 중...")

    query_params = {"action": "expire"}
    body = {} # 이 API 호출에서는 빈 바디를 보냅니다.

    try:
        res = api.put(f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/coupons/{coupon_id}", query_params, body)

        if res.get('code') == 200 and res.get('data') and res['data'].get('content'):
            requested_id = res['data']['content'].get('requestedId')
            if requested_id:
                logger.info(f"[성공] 쿠폰 {coupon_id} (이름: '{coupon_name}') 비활성화 요청 완료. Requested ID: {requested_id}")
                return requested_id
            else:
                logger.warning(f"[주의] 쿠폰 {coupon_id} (이름: '{coupon_name}') 비활성화 요청 성공했으나 Requested ID 없음: {res}")
                return None
        else:
            logger.warning(f"[실패] 쿠폰 {coupon_id} (이름: '{coupon_name}') 비활성화 요청 실패: {res.get('message', '알 수 없는 오류')}")
            return None
    except Exception as e:
        logger.error(f"[실패] 쿠폰 {coupon_id} (이름: '{coupon_name}') 비활성화 중 오류: {e}", exc_info=True)
        return None


def create_new_coupon_util(api: CoupangApiClient, vendor_id: str) -> str | None:
    """
    Coupang API를 통해 새로운 쿠폰을 생성합니다.
    """
    logger.info("[API 생성] 새로운 쿠폰 생성 요청 시도 중...")

    now_kst = datetime.now()
    start_at_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    end_at_str = (now_kst + timedelta(minutes=COUPON_CYCLE_MINUTES + 1)).strftime("%Y-%m-%d %H:%M:%S")

    logger.debug(f"DEBUG: 쿠폰 startAt (로컬 KST): {start_at_str}")
    logger.debug(f"DEBUG: 쿠폰 endAt (로컬 KST): {end_at_str}")

    request_body = {
        "contractId": CONTRACT_ID,
        "name": f"자동쿠폰_{now_kst.strftime('%Y%m%d_%H%M%S')}",
        "discount": COUPON_DISCOUNT_RATE,
        "maxDiscountPrice": COUPON_MAX_DISCOUNT_PRICE,
        "startAt": start_at_str,
        "endAt": end_at_str,
        "type": "RATE",
        "wowExclusive": False
    }

    try:
        res = api.post(f"/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon", request_body)

        if res.get('data', {}).get('success'):
            requested_id = res['data']['content']['requestedId']
            logger.info(f"[성공] 쿠폰 생성 요청 완료 (Requested ID: {requested_id})")
            return requested_id
        else:
            logger.warning(f"[실패] 쿠폰 생성 API 응답 실패: {res.get('code', 'N/A')} - {res.get('message', '알 수 없는 오류')}")
            return None
    except Exception as e:
        logger.error(f"[실패] 쿠폰 생성 중 오류 발생: {e}", exc_info=True)
        return None


def check_coupon_status_util(api: CoupangApiClient, vendor_id: str, requested_id: str) -> Tuple[str, int | None]:
    """
    제공된 requestedId를 사용하여 쿠폰 생성/파기/아이템 생성/파기 요청의
    처리 상태를 확인합니다.

    Args:
        api: CoupangApiClient 인스턴스.
        vendor_id: 판매자 ID (쿠팡에서 발급한 고유 코드).
        requested_id: 결과를 조회할 요청 ID.

    Returns:
        튜플 (status_string, coupon_id_or_none)을 반환합니다.
        - status_string: "DONE", "FAIL", "REQUESTED", "ERROR" 중 하나.
        - coupon_id_or_none: 요청이 성공적으로 완료(DONE)되었을 경우 쿠폰 ID(int), 그 외의 경우 None.
    """
    logger.info(f"[API 조회] 쿠폰 요청 {requested_id} 상태 확인 중...")
    

    try:
        res = api.get(f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/requested/{requested_id}")

        if res.get('code') == 200 and res.get('data') and res['data'].get('content'):
            content = res['data']['content']
            status = content.get('status')
            coupon_id = content.get('couponId')
            request_type = content.get('type')
            succeeded_count = content.get('succeeded', 0)
            failed_count = content.get('failed', 0)
            total_count = content.get('total', 0)

            if status == "DONE":
                logger.info(f"[성공] 쿠폰 요청 {requested_id} (타입: {request_type}) 성공. 상태: DONE, 쿠폰 ID: {coupon_id}, 성공: {succeeded_count}/{total_count}")
                return "DONE", coupon_id
            elif status == "FAIL":
                fail_reason = content.get('reason', '상세 이유 없음')
                error_message_from_data = res['data'].get('errorMessage', 'N/A')
                logger.warning(f"[실패] 쿠폰 요청 {requested_id} (타입: {request_type}) 실패. 상태: FAIL, 실패 개수: {failed_count}/{total_count}, 이유: {fail_reason}, API응답 오류메시지: {error_message_from_data}")
                return "FAIL", None
            elif status == "REQUESTED":
                logger.info(f"[확인중] 쿠폰 요청 {requested_id} (타입: {request_type}) 진행 중. 현재 상태: {status}")
                return "REQUESTED", None
            else:
                logger.warning(f"[경고] 쿠폰 요청 {requested_id} (타입: {request_type}) 알 수 없는 상태: {status}")
                return "ERROR", None
        else:
            error_message_from_res = res.get('message', '알 수 없는 오류')
            error_details_from_data = res.get('data', {}).get('errorMessage', '')
            logger.warning(f"[실패] 쿠폰 요청 {requested_id} 상태 조회 실패. API 응답 코드: {res.get('code', 'N/A')}, 메시지: {error_message_from_res}, 상세: {error_details_from_data}")
            return "ERROR", None
    except Exception as e:
        logger.error(f"[실패] 쿠폰 요청 {requested_id} 상태 조회 중 예외 발생: {e}", exc_info=True)
        return "ERROR", None


def apply_coupon_to_items_util(api: CoupangApiClient, vendor_id: str, coupon_id: int, vendor_items: List[Dict[str, Any]]) -> str | None:
    """
    생성된 쿠폰을 특정 품목에 적용하고, 요청 ID를 반환합니다.
    """
    logger.info(f"[API 적용] 쿠폰 {coupon_id}를 {len(vendor_items)}개 품목에 적용 시도 중...")

    if not vendor_items:
        logger.warning("적용할 VENDOR_ITEMS가 없어 쿠폰 적용을 건너뛰니다.")
        return None

    # body를 명확히 분리
    request_body = {"vendorItems": vendor_items}

    try:
        res = api.post(f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/coupons/{coupon_id}/items", request_body)

        if res.get('data', {}).get('success'):
            requested_id = res['data']['content'].get('requestedId')
            if requested_id:
                logger.info(f"[성공] 쿠폰 {coupon_id} 품목 적용 요청 완료. Requested ID: {requested_id}")
                return requested_id
            else:
                logger.warning(f"[주의] 쿠폰 {coupon_id} 품목 적용 요청 성공했으나 Requested ID 없음: {res}")
                return None
        else:
            logger.warning(f"[실패] 쿠폰 {coupon_id} 품목 적용 API 응답 실패: {res}")
            return None
    except Exception as e:
        logger.error(f"[실패] 쿠폰 {coupon_id} 품목 적용 중 오류 발생: {e}", exc_info=True)
        return None