# coupang_lib/git_utils.py
import subprocess
from coupang_lib.logger import logger

def _run_git_command(command: list[str]) -> str | None:
    """
    Git 명령어를 실행하고 표준 출력을 반환합니다.
    오류 발생 시 None을 반환하고 로깅합니다.
    """
    try:
        logger.debug(f"Git 명령어 실행 시도: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        if result.stderr:
            logger.debug(f"Git 명령어 표준 에러 출력 (경고/정보): {' '.join(command)} -> {result.stderr.strip()}")
        logger.debug(f"Git 명령어 성공: {' '.join(command)}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git 명령어 실행 오류: {' '.join(command)}")
        logger.error(f"오류 코드: {e.returncode}, 표준 출력: {e.stdout.strip()}, 표준 에러: {e.stderr.strip()}")
        return None
    except FileNotFoundError:
        logger.error(f"Git 명령어를 찾을 수 없습니다. Git이 설치되어 있고 PATH에 추가되었는지 확인하세요.")
        return None
    except Exception as e:
        logger.error(f"알 수 없는 오류로 Git 명령어 실행 실패: {e}")
        return None

def check_for_git_updates() -> str:
    """
    원격 업데이트 내역을 확인하고,
    내부 로깅만 수행하며 사용자에게는 간결하고 커밋 메시지가 포함된 업데이트 확인 메시지를 반환합니다.
    """
    logger.debug("원격 업데이트 확인 시작 (디버깅 목적)")
    
    # 사용자에게 보여줄 메시지를 구성할 리스트
    user_friendly_lines = []

    # 1. git fetch 실행하여 원격 최신 정보 가져오기
    fetch_success = True
    fetch_output = _run_git_command(["git", "fetch", "origin"])
    
    if fetch_output is None:
        fetch_success = False
        logger.warning("업데이트 서버 통신 중 문제가 발생했습니다. 업데이트 확인이 정확하지 않을 수 있습니다.")
    else:
        logger.debug("업데이트 정보 가져오기 성공.")

    # 2. 현재 브랜치 이름 가져오기 (이 정보는 로깅 목적으로만 사용되며, 출력 메시지에는 포함되지 않음)
    current_branch = _run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not current_branch:
        current_branch = "main" # 기본값으로 'main' 사용
        logger.warning(f"현재 브랜치 정보를 가져올 수 없습니다. '{current_branch}' 기준으로 확인합니다.")
    logger.debug(f"현재 작업 브랜치: {current_branch}")
    
    # 사용자에게 보여줄 메시지 시작 (브랜치 정보는 제외됨)


    # 업데이트 정보 가져오기 성공 시에만 업데이트 목록 확인 시도
    if fetch_success:
        # 3. 로컬과 원격 정보 비교하여 업데이트 내역 가져오기
        update_log_command = [
            "git", "log", f"HEAD..origin/{current_branch}", # Git 명령어 자체는 특정 브랜치 참조 필요
            "--pretty=format:• %s (%cd)", # 커밋 메시지 본문과 날짜 포함
            "--date=format:%Y-%m-%d %H:%M", # 날짜 포맷 지정
            "--no-merges"
        ]
        raw_update_list = _run_git_command(update_log_command)

        if raw_update_list:
            update_commits = raw_update_list.split('\n')
            num_updates = len(update_commits)
            
            # 사용자 친화적 메시지 구성 (Discord/콘솔) - 브랜치 정보 없음
            user_friendly_lines.append(f"[성공] 새로운 업데이트 {num_updates}개 발견!")
            user_friendly_lines.append("--- 업데이트 내용 ---")
            user_friendly_lines.extend(update_commits) # 각 커밋 메시지를 '• 메시지 (날짜 시간)' 형태로 추가
            user_friendly_lines.append("---------------------")

            # 프로그램 로그 (logger.info) 형식 - 브랜치 정보 제거
            logger.info(f"--- 업데이트 보고 ({num_updates}개 발견) ---") # 브랜치명 제거
            for commit_msg in update_commits:
                logger.info(f"  {commit_msg}") # 들여쓰기와 함께 커밋 메시지 출력
            logger.info("--- 보고 종료 ---")

        else:
            user_friendly_lines.append("새로운 업데이트가 없습니다. 현재 최신 버전입니다.")
            logger.info("--- 업데이트 보고: 새로운 업데이트 없음 ---")
    else:
        user_friendly_lines.append("[경고] 업데이트 확인 중 오류 발생. (자세한 내용은 로그 확인)")
        logger.warning("--- 업데이트 보고: 업데이트 확인 실패 ---")

    # Discord 메시지용 최종 문자열 (프로그램 업데이트 확인 섹션)
    discord_update_message = f"\n\n**[프로그램 업데이트 확인]**\n```\n" + "\n".join(user_friendly_lines) + "\n```"
    
    return discord_update_message

if __name__ == "__main__":
    from coupang_lib.logger import logger as main_logger
    main_logger.setLevel(logging.DEBUG)
    
    print("--- 업데이트 유틸리티 테스트 시작 (디버그 로그 출력) ---")
    message = check_for_git_updates()
    print("\n--- 생성된 Discord 메시지 미리보기 (간결한 사용자 메시지) ---")
    print(message)
    print("--- 업데이트 유틸리티 테스트 종료 ---")