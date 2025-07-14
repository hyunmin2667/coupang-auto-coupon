# coupang_lib/logger.py
import logging
import os

def setup_logging():
    """
    애플리케이션 전반에 걸쳐 사용할 로깅을 설정합니다.
    콘솔과 파일에 로그를 출력하도록 구성합니다.
    """
    # 로그 파일 경로 설정
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True) # logs 디렉터리가 없으면 생성
    log_file_path = os.path.join(log_dir, "coupang_automation.log")

    # 로거 인스턴스 생성 또는 가져오기
    logger = logging.getLogger("coupang_automation")
    logger.setLevel(logging.DEBUG) # 가장 낮은 DEBUG 레벨부터 모든 로그를 처리

    # 핸들러 설정
    # 1. 콘솔 핸들러: 화면에 로그 출력
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # 콘솔에는 INFO 레벨 이상만 출력 (너무 많은 DEBUG 로그 방지)

    # 2. 파일 핸들러: 로그 파일에 저장 (RotatingFileHandler 사용하여 파일 크기 제한)
    # 1MB까지 기록하고, 5개까지 백업 파일을 유지합니다.
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=1024*1024, # 1MB
        backupCount=5,     # 최대 5개 파일
        encoding='utf-8'   # 한글 로그를 위해 utf-8 인코딩
    )
    file_handler.setLevel(logging.DEBUG) # 파일에는 모든 DEBUG 로그 기록

    # 포맷터 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 기존 핸들러가 있다면 제거 (중복 로깅 방지)
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

# 스크립트 전반에서 사용할 로거 인스턴스를 초기화
logger = setup_logging()