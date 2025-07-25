import subprocess
import logging

def _run_git_command(command: list[str], logger: logging.Logger) -> str | None:
    """
    Git 명령어를 실행하고 표준 출력을 반환합니다.
    오류 발생 시 None을 반환하고 로깅합니다.
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        # Git fetch 같은 명령은 stdout이 비어있을 수 있으므로, stderr도 함께 로깅하여 정보 확인
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

def check_for_git_updates(logger: logging.Logger) -> str:
    """
    Git 원격 저장소의 업데이트 내역을 확인하고,
    내부 로깅만 수행하며 사용자에게는 간결한 업데이트 확인 메시지를 반환합니다.
    """
    logger.debug("Git 원격 저장소 업데이트 확인 시작 (디버깅 목적)")
    
    # 사용자에게 보여줄 메시지를 구성할 변수
    user_friendly_message = ""

    # 1. git fetch 실행하여 원격 최신 정보 가져오기
    fetch_success = True
    fetch_output = _run_git_command(["git", "fetch", "origin"], logger)
    
    if fetch_output is None:
        fetch_success = False
        logger.warning("Git fetch 실행 중 문제가 발생했습니다. 업데이트 확인이 정확하지 않을 수 있습니다.")
    else:
        logger.debug("Git fetch 성공.")

    # 2. 현재 브랜치 이름 가져오기
    current_branch = _run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], logger)
    if not current_branch:
        current_branch = "main"
        logger.warning(f"현재 Git 브랜치 이름을 가져올 수 없습니다. '{current_branch}' 기준으로 확인합니다.")
    logger.debug(f"현재 작업 브랜치: {current_branch}")

    # Git fetch가 성공했을 때만 업데이트 목록 확인 시도
    if fetch_success:
        # 3. 로컬 브랜치와 원격 브랜치 비교하여 업데이트 내역 가져오기
        update_log_command = ["git", "log", f"HEAD..origin/{current_branch}", "--pretty=format:%s (ID: %h)", "--no-merges"]
        raw_update_list = _run_git_command(update_log_command, logger)

        if raw_update_list:
            update_commits = raw_update_list.split('\n')
            num_updates = len(update_commits)
            
            user_friendly_message = f"새로운 업데이트 {num_updates}개가 발견되었습니다."
            logger.info(f"--- 원격 저장소 업데이트 {num_updates}개 발견 ({current_branch}) ---")
            for commit_msg in update_commits:
                logger.info(f"  - {commit_msg}")
            logger.info("---------------------------------------------")
        else:
            user_friendly_message = "새로운 업데이트가 없습니다. 현재 최신 버전입니다."
            logger.info("원격 저장소에 새로운 업데이트가 없습니다.")
    else:
        user_friendly_message = "업데이트 확인 중 오류가 발생했습니다. (자세한 내용은 로그 확인)"
        logger.warning("Git fetch 실패로 인해 업데이트 목록을 확인할 수 없습니다.")

    # Discord 메시지용 최종 문자열 (프로그램 업데이트 확인 섹션)
    discord_update_message = f"\n\n**[프로그램 업데이트 확인]**\n```\n{user_friendly_message}\n```"
    
    return discord_update_message

if __name__ == "__main__":
    # 모듈 테스트를 위한 로거 설정 (디버그 레벨로 설정하여 Git 상세 로그 확인)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    test_logger = logging.getLogger(__name__)
    
    print("--- Git 업데이트 유틸리티 테스트 시작 (디버그 로그 출력) ---")
    message = check_for_git_updates(test_logger)
    print("\n--- 생성된 Discord 메시지 미리보기 (간결한 사용자 메시지) ---")
    print(message)
    print("--- Git 업데이트 유틸리티 테스트 종료 ---")