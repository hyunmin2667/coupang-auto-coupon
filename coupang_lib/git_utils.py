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
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git 명령어 실행 오류: {' '.join(command)}")
        logger.error(f"오류 코드: {e.returncode}, 표준 출력: {e.stdout.strip()}, 표준 에러: {e.stderr.strip()}")
        return None
    except Exception as e:
        logger.error(f"알 수 없는 오류로 Git 명령어 실행 실패: {e}")
        return None

def check_for_git_updates(logger: logging.Logger) -> str:
    """
    Git 원격 저장소의 업데이트 내역을 확인하고 프로그램처럼 보이는 메시지 문자열을 반환합니다.
    """
    logger.info("Git 원격 저장소 업데이트 확인 중...")
    
    # Discord 메시지 초기화
    discord_update_message = ""
    program_output_lines = [] # 프로그램처럼 보일 출력 라인들을 저장할 리스트

    # 1. git fetch 실행하여 원격 최신 정보 가져오기
    fetch_result = _run_git_command(["git", "fetch", "origin"], logger)
    if fetch_result:
        logger.info(f"Git fetch 완료.")
    else:
        logger.warning("Git fetch 실행 중 문제가 발생했거나 네트워크 오류가 발생했습니다. 업데이트 확인이 정확하지 않을 수 있습니다.")
        program_output_lines.append("[!] Git 업데이트 확인 중 오류 발생: 네트워크 문제 또는 저장소 접근 불가")
        # fetch 실패 시에도 업데이트 목록 확인은 시도할 수 있도록 함

    # 2. 현재 브랜치 이름 가져오기
    current_branch = _run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], logger)
    if not current_branch:
        current_branch = "main" # 기본 브랜치 이름으로 폴백
        logger.warning(f"현재 Git 브랜치 이름을 가져올 수 없습니다. '{current_branch}' 기준으로 확인합니다.")
    
    program_output_lines.append(f"[INFO] 현재 작업 브랜치: {current_branch}")

    # 3. 로컬 브랜치와 원격 브랜치 비교하여 업데이트 내역 가져오기
    # `--pretty=format:%s`를 사용하여 커밋 메시지 제목만 가져오고, `--abbrev-commit`으로 짧은 해시 사용
    update_log_command = ["git", "log", f"HEAD..origin/{current_branch}", "--pretty=format:• %s (ID: %h)", "--no-merges"]
    raw_update_list = _run_git_command(update_log_command, logger)

    if raw_update_list:
        update_commits = raw_update_list.split('\n')
        num_updates = len(update_commits)
        
        program_output_lines.append(f"[SUCCESS] 새로운 업데이트 {num_updates}개 발견!")
        program_output_lines.append("--- 업데이트 내용 ---")
        program_output_lines.extend(update_commits) # 각 커밋 메시지를 라인별로 추가
        program_output_lines.append("---------------------")
        
        # Discord 메시지용 문자열 구성 (코드 블록 안에 넣어 가독성 높임)
        discord_update_message = "\n\n**[프로그램 업데이트 확인]**\n```\n" + "\n".join(program_output_lines) + "\n```"
        logger.info("\n" + "\n".join(program_output_lines)) # 로깅에도 깔끔한 프로그램 출력 추가

    else:
        program_output_lines.append("[INFO] 새로운 업데이트가 없습니다. 현재 최신 버전입니다.")
        discord_update_message = "\n\n**[프로그램 업데이트 확인]**\n```\n" + "\n".join(program_output_lines) + "\n```"
        logger.info("\n" + "\n".join(program_output_lines))

    return discord_update_message

if __name__ == "__main__":
    # 모듈 테스트를 위한 간단한 로거 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    test_logger = logging.getLogger(__name__)
    
    print("--- Git 업데이트 유틸리티 테스트 시작 ---")
    message = check_for_git_updates(test_logger)
    print("\n--- 생성된 Discord 메시지 미리보기 ---")
    print(message)
    print("--- Git 업데이트 유틸리티 테스트 종료 ---")