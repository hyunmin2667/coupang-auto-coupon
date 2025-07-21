@echo off
REM Command Prompt의 인코딩을 UTF-8로 변경 (한글 깨짐 방지)
chcp 65001 > nul

REM 가상 환경 비활성화
echo 가상 환경 비활성화 중...
deactivate 2>nul

REM 가상 환경 존재 여부 확인 및 생성
echo 가상 환경 확인 및 활성화 중...
IF NOT EXIST ".venv\" (
    echo .venv 가상 환경이 존재하지 않습니다. 생성 중...
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo 가상 환경 생성 실패. Python이 설치되어 있고 PATH에 있는지 확인하세요.
        pause
        exit /b 1
    )
    echo 가상 환경 생성 완료.
)

REM 가상 환경 활성화
REM 가상 환경 경로가 현재 디렉토리의 .venv 폴더 안에 있다고 가정합니다.
REM 만약 가상 환경의 경로가 다르다면 아래 경로를 수정해주세요.
call .venv\Scripts\activate
IF %ERRORLEVEL% NEQ 0 (
    echo 가상 환경 활성화 실패. .venv\Scripts\activate 경로를 확인하세요.
    pause
    exit /b 1
)
echo 가상 환경 활성화 완료.

REM 필요한 패키지 설치
echo 필요한 패키지를 설치 중입니다...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo 패키지 설치 실패. requirements.txt 파일을 확인하거나 인터넷 연결 상태를 확인하세요.
    pause
    exit /b 1
)
echo 패키지 설치 완료.

REM main.py 스크립트 실행
echo main.py 실행 중...
python main.py

echo.
echo 스크립트 실행이 완료되었습니다.
echo.
echo *만약 정상적으로 동작하지 않았다면, 스크립트를 다시 실행해보세요!*
pause