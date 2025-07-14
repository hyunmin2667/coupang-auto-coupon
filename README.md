# Coupang 자동 쿠폰 갱신 스크립트

이 프로젝트는 Coupang API 및 Selenium을 활용하여 판매자 쿠폰을 자동으로 관리하고 갱신하는 Python 스크립트입니다. 기존에 활성화된 특정 쿠폰을 비활성화하고, 새로운 쿠폰을 생성하여 지정된 품목에 자동으로 적용합니다. 모든 과정은 로깅되며, Discord 웹훅을 통해 알림을 받아볼 수 있습니다.

## 주요 기능

  * **자동 쿠폰 비활성화**: API를 사용하여 이전에 생성된 "자동쿠폰\_" 이름의 활성 쿠폰을 자동으로 조회하고 비활성화합니다.
  * **새 쿠폰 생성**: 현재 시간을 기준으로 새로운 할인율 및 최대 할인 금액이 적용된 쿠폰을 생성합니다.
  * **품목에 쿠폰 적용**: `vendor_items.csv` 파일에 정의된 품목(상품 ID)들에 새로 생성된 쿠폰을 자동으로 적용합니다.
  * **스케줄링**: 설정된 시간(기본 60분)마다 전체 쿠폰 갱신 사이클을 자동으로 실행합니다.
  * **Discord 알림**: 쿠폰 자동화 사이클의 성공 또는 실패 여부를 Discord 웹훅으로 실시간 알림합니다.
  * **상세 로깅**: 모든 작업 과정과 오류는 콘솔 및 로그 파일(`logs/coupang_automation.log`)에 기록됩니다.
  * **Selenium 대안/보조**: 필요에 따라 Selenium을 사용하여 쿠팡 WING에 로그인하고 쿠폰을 비활성화하는 기능도 포함되어 있습니다. (현재 `main.py`는 API 기반 비활성화를 우선합니다.)

## 기술 스택

  * **Python 3.x**
  * **pandas**: CSV 파일에서 품목 데이터를 로드합니다.
  * **selenium**: 웹 자동화를 위한 라이브러리 (필요시 사용).
  * **webdriver-manager**: Selenium 웹드라이버를 자동으로 관리합니다.
  * **schedule**: 스크립트 실행 스케줄링을 담당합니다.
  * **python-dotenv/dotenv**: 환경 변수를 `.env` 파일에서 로드합니다.
  * **requests**: Discord 웹훅 통신에 사용됩니다.
  * **hmac, hashlib, urllib.request, urllib.parse**: 쿠팡 API 인증 및 요청 처리에 사용됩니다.

## 시작하기

### 1\. 저장소 클론

```bash
git clone https://github.com/hyunmin2667/coupang-auto-coupon.git
cd coupang-auto-coupon
```

### 2\. 수동 가상 환경 설정 및 의존성 설치

1.  **가상 환경 생성**:
    프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 `.venv`라는 이름의 가상 환경을 생성합니다.

    ```bash
    python -m venv .venv
    ```

    만약 `python` 명령어를 찾을 수 없다는 오류가 발생하면, Python이 제대로 설치되었는지, 그리고 환경 변수(PATH)에 추가되었는지 확인해야 합니다.

2.  **가상 환경 활성화**:
    생성된 가상 환경을 활성화합니다.

      * **macOS/Linux**:
        ```bash
        source ./.venv/bin/activate
        ```
      * **Windows (명령 프롬프트/CMD)**:
        ```bash
        .venv\Scripts\activate
        ```
      * **Windows (PowerShell)**:
        ```powershell
        .venv\Scripts\Activate.ps1
        ```

3.  **필수 패키지 설치**:
    가상 환경이 활성화된 상태에서 `requirements.txt`에 명시된 모든 패키지를 설치합니다.

    ```bash
    pip install -r requirements.txt
    ```

### 3\. 환경 변수 설정 (`.env` 파일)

이 프로젝트는 민감한 정보를 `.env` 파일에서 로드합니다. 저장소에 포함된 `.env.example` 파일을 참조하여 `.env` 파일을 생성하고 필요한 정보를 입력하세요.

1.  프로젝트 루트 디렉토리에서 `.env.example` 파일을 `.env`로 복사하거나 이름을 변경합니다.
2.  `.env` 파일을 열고 다음과 같이 각 변수에 실제 계정 정보나 발급받은 키 값을 입력합니다. **`"your_..."`로 표시된 부분을 실제 값으로 반드시 변경해야 합니다.**

<!-- end list -->

```dotenv
# 쿠폰 할인율 (예: 50% 할인)
COUPON_DISCOUNT_RATE=50

# 쿠폰 최대 할인 금액 (예: 5000원)
COUPON_MAX_DISCOUNT_PRICE=5000

# 자동화 스케줄 설정 : 쿠폰 갱신 사이클 시간 (분 단위, 예: 60분)
COUPON_CYCLE_MINUTES=60

# 기본설정
COUPANG_ID="your_coupang_id"
COUPANG_PW="your_coupang_password"

ACCESS_KEY="your_access_key"
SECRET_KEY="your_secret_key"

VENDOR_ID="your_vendor_id"
CONTRACT_ID=10

DISCORD_WEBHOOK_URL="your_discord_webhook_url"
```

**주의**: `.env` 파일은 민감한 정보를 포함하므로 Git 저장소에 커밋되지 않도록 `.gitignore`에 추가되어 있습니다.

### 4\. 품목 데이터 준비 (`vendor_items.csv`)

- 프로젝트 루트 디렉토리에 `vendor_items.csv` 파일이 존재해야 합니다.
- 이 파일은 쿠폰을 적용할 상품의 ID를 한 줄에 하나씩 포함해야 합니다.
- 헤더 없이 상품 ID만 나열합니다.

```csv
92796688288
92796688320
92796688298
...
```

## 스크립트 실행

위의 모든 설정 (가상 환경 생성/패키지 설치, `.env` 설정, `vendor_items.csv` 준비)이 완료된 후, 다음 스크립트를 사용하여 `main.py`를 실행할 수 있습니다. 이 스크립트는 가상 환경을 활성화하고 `main.py`를 실행하는 역할을 합니다.

  * **macOS/Linux (`mac_run.sh`)**:
    ```bash
    # 실행 권한 부여
    chmod +x mac_run.sh
    # 스크립트 실행
    ./mac_run.sh
    ```
  * **Windows (배치 파일 - `run.bat` 실행)**:

## 파일 구조

```
.
├── .env                  # 환경 변수 설정 파일 (사용자가 생성, .gitignore에 포함)
├── .gitignore            # Git 무시 파일
├── .env.example           # .env 파일 생성을 위한 예시 파일
├── main.py               # 메인 스크립트 (쿠폰 자동화 로직)
├── requirements.txt      # Python 의존성 목록
├── vendor_items.csv      # 쿠폰 적용 대상 품목 ID (사용자가 생성)
├── coupang_lib/
│   ├── __init__.py
│   ├── api_client.py         # 쿠팡 API 통신 클라이언트
│   ├── config.py             # 설정 변수 로드 및 관리
│   ├── coupang_api_utils.py  # 쿠팡 API 호출 유틸리티 함수
│   ├── coupang_wing_selenium.py # Selenium 기반 쿠팡 WING 자동화 (대안)
│   ├── discord_notifier.py   # Discord 알림 전송 기능
│   ├── item_loader.py        # vendor_items.csv 파일 로드 기능
│   └── logger.py             # 로깅 설정
└── logs/                 # 스크립트 실행 로그 저장 디렉토리 (자동 생성)
    └── coupang_automation.log
```