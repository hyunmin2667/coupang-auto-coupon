# coupang_lib/config.py
import os
from dotenv import load_dotenv

load_dotenv() # .env 파일 로드

# 쿠팡 API 인증 정보
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
VENDOR_ID = os.getenv("VENDOR_ID")
CONTRACT_ID = os.getenv("CONTRACT_ID") # .env 파일에 유효한 값이 채워져 있어야 합니다.

# 쿠팡 WING 로그인 정보 (Selenium 사용)
COUPANG_ID = os.getenv("COUPANG_ID")
COUPANG_PW = os.getenv("COUPANG_PW")

# API Gateway 기본 URL
API_GATEWAY_URL = "https://api-gateway.coupang.com"

# Selenium 옵션 (GUI 없이 실행)
SELENIUM_HEADLESS = True
SELENIUM_WINDOW_SIZE = "1920,1080"

# DISCORD Webhook 설정
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# --- 추가된 쿠폰 및 스케줄 설정 ---
# getenv로 값을 가져올 때, 정수형으로 변환하고 기본값을 설정하여 안전성을 높입니다.
# .env 파일에 값이 없거나 잘못된 형식일 경우를 대비합니다.
COUPON_DISCOUNT_RATE = int(os.getenv("COUPON_DISCOUNT_RATE", "50"))
COUPON_MAX_DISCOUNT_PRICE = int(os.getenv("COUPON_MAX_DISCOUNT_PRICE", "5000"))
COUPON_CYCLE_MINUTES = int(os.getenv("COUPON_CYCLE_MINUTES", "60"))