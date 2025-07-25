import subprocess
from coupang_lib.logger import logger

def _run_git_command(command: list[str], logger_instance=logger) -> str | None: # logger_instance를 기본값으로 설정
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
        if result.stderr:
            logger_instance.debug(f"Git 명령어 표준 에러 출력 (경고/정보): {' '.join(command)} -> {result.stderr.strip()}")
        logger_instance.debug(f"Git 명령어 성공: {' '.join(command)}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger_instance.error(f"Git 명령어 실행 오류: {' '.join(command)}")
        logger_instance.error(f"오류 코드: {e.returncode}, 표준 출력: {e.stdout.strip()}, 표준 에러: {e.stderr.strip()}")
        return None
    except FileNotFoundError:
        logger_instance.error(f"Git 명령어를 찾을 수 없습니다. Git이 설치되어 있고 PATH에 추가되었는지 확인하세요.")
        return None
    except Exception as e:
        logger_instance.error(f"알 수 없는 오류로 Git 명령어 실행 실패: {e}")
        return None

def check_for_git_updates(logger_instance=logger) -> str: # logger_instance를 기본값으로 설정
    """
    Git 원격 저장소의 업데이트 내역을 확인하고,
    내부 로깅만 수행하며 사용자에게는 간결한 업데이트 확인 메시지를 반환합니다.
    """
    logger_instance.debug("Git 원격 저장소 업데이트 확인 시작 (디버깅 목적)")
    
    user_friendly_message = ""

    fetch_success = True
    fetch_output = _run_git_command(["git", "fetch", "origin"], logger_instance)
    
    if fetch_output is None:
        fetch_success = False
        logger_instance.warning("Git fetch 실행 중 문제가 발생했습니다. 업데이트 확인이 정확하지 않을 수 있습니다.")
    else:
        logger_instance.debug("Git fetch 성공.")

    current_branch = _run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], logger_instance)
    if not current_branch:
        current_branch = "main"
        logger_instance.warning(f"현재 Git 브랜치 이름을 가져올 수 없습니다. '{current_branch}' 기준으로 확인합니다.")
    logger_instance.debug(f"현재 작업 브랜치: {current_branch}")

    if fetch_success:
        update_log_command = ["git", "log", f"HEAD..origin/{current_branch}", "--pretty=format:%s (ID: %h)", "--no-merges"]
        raw_update_list = _run_git_command(update_log_command, logger_instance)

        if raw_update_list:
            update_commits = raw_update_list.split('\n')
            num_updates = len(update_commits)
            
            user_friendly_message = f"새로운 업데이트 {num_updates}개가 발견되었습니다."
            logger_instance.info(f"--- 원격 저장소 업데이트 {num_updates}개 발견 ({current_branch}) ---")
            for commit_msg in update_commits:
                logger_instance.info(f"  - {commit_msg}")
            logger_instance.info("---------------------------------------------")
        else:
            user_friendly_message = "새로운 업데이트가 없습니다. 현재 최신 버전입니다."
            logger_instance.info("원격 저장소에 새로운 업데이트가 없습니다.")
    else:
        user_friendly_message = "업데이트 확인 중 오류가 발생했습니다. (자세한 내용은 로그 확인)"
        logger_instance.warning("Git fetch 실패로 인해 업데이트 목록을 확인할 수 없습니다.")

    discord_update_message = f"\n\n**[프로그램 업데이트 확인]**\n```\n{user_friendly_message}\n```"
    
    return discord_update_message

if __name__ == "__main__":
    # coupang_lib.logger.py에서 설정된 logger를 사용하므로 여기서 추가 설정 불필요
    # 테스트를 위해 logger 레벨을 DEBUG로 설정하여 상세 로그 확인 가능
    logger.setLevel(logging.DEBUG) 
    
    print("--- Git 업데이트 유틸리티 테스트 시작 (디버그 로그 출력) ---")
    message = check_for_git_updates() # logger 인자 없이 호출 가능
    print("\n--- 생성된 Discord 메시지 미리보기 (간결한 사용자 메시지) ---")
    print(message)
    print("--- Git 업데이트 유틸리티 테스트 종료 ---")