# coupang_lib/git_utils.py
import subprocess
from coupang_lib.logger import logger # coupang_lib.logger에서 logger 인스턴스를 가져옵니다.

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
            check=True, # 이 부분이 오류 발생 시 CalledProcessError를 발생시킵니다.
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
    Git 원격 저장소의 업데이트 내역을 확인하고,
    내부 로깅만 수행하며 사용자에게는 간결하고 커밋 메시지가 포함된 업데이트 확인 메시지를 반환합니다.
    """
    logger.debug("Git 원격 저장소 업데이트 확인 시작 (디버깅 목적)")
    
    # 사용자에게 보여줄 메시지를 구성할 리스트
    user_friendly_lines = []

    # 1. git fetch 실행하여 원격 최신 정보 가져오기
    fetch_success = True
    fetch_output = _run_git_command(["git", "fetch", "origin"])
    
    if fetch_output is None:
        fetch_success = False
        logger.warning("Git fetch 실행 중 문제가 발생했습니다. 업데이트 확인이 정확하지 않을 수 있습니다.")
    else:
        logger.debug("Git fetch 성공.")

    # 2. 현재 브랜치 이름 가져오기
    current_branch = _run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not current_branch:
        current_branch = "main"
        logger.warning(f"현재 Git 브랜치 이름을 가져올 수 없습니다. '{current_branch}' 기준으로 확인합니다.")
    logger.debug(f"현재 작업 브랜치: {current_branch}")
    
    # 사용자에게 보여줄 메시지 시작
    user_friendly_lines.append(f"[정보] 현재 브랜치: {current_branch}")


    # Git fetch가 성공했을 때만 업데이트 목록 확인 시도
    if fetch_success:
        # 3. 로컬 브랜치와 원격 브랜치 비교하여 업데이트 내역 가져오기
        update_log_command = ["git", "log", f"HEAD..origin/{current_branch}", "--pretty=format:• %s (ID: %h)", "--no-merges"]
        raw_update_list = _run_git_command(update_log_command)

        if raw_update_list:
            update_commits = raw_update_list.split('\n')
            num_updates = len(update_commits)
            
            user_friendly_lines.append(f"[성공] 새로운 업데이트 {num_updates}개 발견!")
            user_friendly_lines.append("--- 업데이트 내용 ---")
            user_friendly_lines.extend(update_commits) # 각 커밋 메시지를 라인별로 추가
            user_friendly_lines.append("---------------------")

            logger.info(f"--- 원격 저장소 업데이트 {num_updates}개 발견 ({current_branch}) ---")
            for commit_msg in update_commits:
                logger.info(f"  - {commit_msg}")
            logger.info("---------------------------------------------")

        else:
            user_friendly_lines.append("새로운 업데이트가 없습니다. 현재 최신 버전입니다.")
            logger.info("원격 저장소에 새로운 업데이트가 없습니다.")
    else:
        user_friendly_lines.append("[경고] 업데이트 확인 중 오류 발생. (Git fetch 실패, 자세한 내용은 로그 확인)")
        logger.warning("Git fetch 실패로 인해 업데이트 목록을 확인할 수 없습니다.")

    # Discord 메시지용 최종 문자열 (프로그램 업데이트 확인 섹션)
    discord_update_message = f"\n\n**[프로그램 업데이트 확인]**\n```\n" + "\n".join(user_friendly_lines) + "\n```"
    
    return discord_update_message

if __name__ == "__main__":
    # coupang_lib.logger.py에서 설정된 logger를 사용하므로 여기서 추가 설정 불필요
    # logger.setLevel(logging.DEBUG)  # 이 줄이 불필요하여 제거되었습니다.
    
    print("--- Git 업데이트 유틸리티 테스트 시작 (디버그 로그 출력) ---")
    message = check_for_git_updates() # logger 인자 없이 호출 가능
    print("\n--- 생성된 Discord 메시지 미리보기 (간결한 사용자 메시지) ---")
    print(message)
    print("--- Git 업데이트 유틸리티 테스트 종료 ---")