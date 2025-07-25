import json
import hmac
import hashlib
import os
import time
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timezone

from coupang_lib.config import ACCESS_KEY, SECRET_KEY, API_GATEWAY_URL
from coupang_lib.logger import logger

class CoupangApiClient:
    def __init__(self, access_key: str, secret_key: str, api_gateway_url: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.api_gateway_url = api_gateway_url

    def _generate_signature(self, method: str, path_without_query: str, query_string_encoded: str = "") -> str:
        """
        쿠팡 API 호출을 위한 HMAC SHA256 서명을 생성합니다.
        signed-date를 명시적으로 UTC 기준으로 생성합니다 (공식 가이드의 YYMMDDTHHMMSSZ 패턴).
        """
        current_utc_time = datetime.now(timezone.utc)
        gmt_time_str = current_utc_time.strftime('%y%m%d') + 'T' + current_utc_time.strftime('%H%M%S') + 'Z'
        
        message_to_sign = f"{gmt_time_str}{method}{path_without_query}{query_string_encoded}"
        logger.debug(f"Signature Message String: {message_to_sign}")
        
        message_bytes = message_to_sign.encode('utf-8')
        signature = hmac.new(self.secret_key.encode('utf-8'), message_bytes, hashlib.sha256).hexdigest()
        
        return f"CEA algorithm=HmacSHA256, access-key={self.access_key}, signed-date={gmt_time_str}, signature={signature}"

    def send_request(self, method: str, path_without_query: str, query_params: dict = None, body: dict = None):
        if query_params is None:
            query_params = {}
        query_string_encoded = urllib.parse.urlencode(query_params)
        full_url = f"{self.api_gateway_url}{path_without_query}"
        if query_string_encoded:
            full_url += f"?{query_string_encoded}"
        
        authorization_header = self._generate_signature(method, path_without_query, query_string_encoded)
        headers = {
            "Authorization": authorization_header,
            "Content-Type": "application/json;charset=UTF-8"
        }
        req_body = json.dumps(body).encode('utf-8') if body else None
        
        # 변경: API 요청 상세 로그를 DEBUG 레벨로 변경
        logger.debug(f"\n--- API 요청 상세 ({method} {path_without_query}) ---")
        logger.debug(f"요청 URL: {full_url}")
        logger.debug(f"요청 메소드: {method}")
        logger.debug(f"요청 헤더 Authorization: {headers['Authorization']}") # 민감 정보이므로 DEBUG로
        if req_body:
            # 바디가 있을 경우에만 로깅 (POST/PUT 등에 해당)
            logger.debug(f"요청 바디: {json.dumps(body, indent=2, ensure_ascii=False)}") # 상세 정보이므로 DEBUG로
        logger.debug("---------------------------------------------")
        
        try:
            req = urllib.request.Request(full_url, data=req_body, headers=headers, method=method) if req_body else urllib.request.Request(full_url, headers=headers, method=method)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                raw_response_bytes = resp.read()
                charset = resp.headers.get_content_charset() or 'utf-8'
                
                response_body = ""
                try:
                    response_body = raw_response_bytes.decode(charset)
                except UnicodeDecodeError:
                    logger.warning(f"WARNING: '{charset}' 디코딩 실패, 'cp949'로 재시도.")
                    try:
                        response_body = raw_response_bytes.decode('cp949')
                    except UnicodeDecodeError:
                        logger.warning(f"WARNING: 'cp949' 디코딩 실패, 'euc-kr'로 재시도.")
                        try:
                            response_body = raw_response_bytes.decode('euc-kr')
                        except UnicodeDecodeError:
                            response_body = raw_response_bytes.decode('latin-1', errors='ignore')
                            logger.warning(f"WARNING: 모든 디코딩 시도 실패, 'latin-1'으로 디코딩 (데이터 손실 가능).")
                except Exception as decode_e:
                    logger.error(f"ERROR: 응답 본문 디코딩 중 예상치 못한 오류: {decode_e}")
                    response_body = raw_response_bytes.decode('latin-1', errors='ignore')


                res = json.loads(response_body)
                
                # 변경: API 응답 상세 로그를 DEBUG 레벨로 변경
                logger.debug(f"\n--- API 응답 ({method} {path_without_query}) ---")
                logger.debug(f"HTTP 상태 코드: {resp.getcode()}")
                logger.debug(f"응답 본문: {json.dumps(res, indent=2, ensure_ascii=False)}") # 상세 정보이므로 DEBUG로
                logger.debug("--------------------")
                return res
        except urllib.error.HTTPError as e:
            error_response_body = e.read()
            charset = e.headers.get_content_charset() or 'utf-8'
            try:
                error_response_text = error_response_body.decode(charset)
            except UnicodeDecodeError:
                try:
                    error_response_text = error_response_body.decode('cp949')
                except UnicodeDecodeError:
                    error_response_text = error_response_body.decode('euc-kr')
                except Exception:
                    error_response_text = error_response_body.decode('latin-1', errors='ignore')
                    logger.error(f"ERROR: 오류 응답 본문 디코딩 중 예상치 못한 오류 발생, latin-1으로 처리.")
            except Exception as decode_e:
                error_response_text = error_response_body.decode('latin-1', errors='ignore')
                logger.error(f"ERROR: 오류 응답 본문 디코딩 중 예상치 못한 오류: {decode_e}")

            logger.error(f"\n[실패] HTTP 오류: {e.code} - {e.reason}")
            logger.error(f"오류 응답 본문: {error_response_text}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"\n[실패] URL 오류: {e.reason}")
            logger.error("네트워크 연결 또는 방화벽 문제일 수 있습니다.")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"\n[실패] JSON 디코딩 오류: {e}")
            try:
                logger.error(f"응답을 파싱할 수 없습니다. 수신된 본문: {response_body[:500]}...")
            except NameError:
                logger.error("응답 본문을 가져올 수 없어 파싱할 수 없습니다.")
            raise
        except Exception as e:
            logger.error(f"\n[실패] 예상치 못한 오류가 발생했습니다: {e}")
            raise

    # 래핑된 HTTP 메서드 수정 (인자 전달 방식 개선)
    def get(self, path: str, query_params: dict = None) -> dict:
        """GET 요청을 보냅니다."""
        return self.send_request("GET", path, query_params=query_params, body=None)

    def post(self, path: str, body: dict = None) -> dict:
        """POST 요청을 보냅니다."""
        # POST 요청에서는 쿼리 파라미터가 일반적으로 없으므로 빈 딕셔너리 전달
        return self.send_request("POST", path, query_params={}, body=body)

    def put(self, path: str, query_params: dict = None, body: dict = None) -> dict:
        """PUT 요청을 보냅니다."""
        # put은 기존 코드가 잘 작동했으므로 그대로 유지하지만, 명확성을 위해 body=body 명시
        return self.send_request("PUT", path, query_params=query_params, body=body)

    def delete(self, path: str, query_params: dict = None) -> dict:
        """DELETE 요청을 보냅니다."""
        return self.send_request("DELETE", path, query_params=query_params, body=None)