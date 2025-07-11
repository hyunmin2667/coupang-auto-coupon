#!/bin/bash

# macOS/Linux용 쿠팡 자동화 스크립트
# 터미널 인코딩은 일반적으로 UTF-8이므로 별도 설정 불필요

# echo "가상 환경 비활성화 중..." # 이 줄과 다음 줄을 주석 처리하거나 제거합니다.
# deactivate 2>/dev/null || true

echo "가상 환경 활성화 중..."
# 가상 환경 경로가 현재 디렉토리의 .venv 폴더 안에 있다고 가정합니다.
# 만약 가상 환경의 경로가 다르다면 아래 경로를 수정해주세요.
# macOS/Linux에서는 Scripts 대신 bin 디렉토리에 activate 파일이 있습니다.
VENV_ACTIVATE_SCRIPT="./.venv/bin/activate"

if [ -f "$VENV_ACTIVATE_SCRIPT" ]; then
    source "$VENV_ACTIVATE_SCRIPT"
    echo "가상 환경 활성화 완료."
else
    echo "오류: $VENV_ACTIVATE_SCRIPT 파일을 찾을 수 없습니다." >&2
    echo "가상 환경이 없거나 경로가 잘못되었습니다. 가상 환경을 생성하거나 경로를 수정해주세요." >&2
    exit 1 # 스크립트 종료
fi

echo "main.py 실행 중..."
python main.py

echo ""
echo "스크립트 실행이 완료되었습니다."
# 아무 키나 누르면 계속 진행 (macOS/Linux에서 Windows의 pause와 유사)
read -n 1 -s -r -p "계속하려면 아무 키나 누르세요..."
echo "" # 개행 추가