# coupang_lib/coupang_wing_selenium.py
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
# config.py에서 변수 임포트 (상대 경로를 절대 경로로 변경)
from coupang_lib.config import COUPANG_ID, COUPANG_PW, SELENIUM_HEADLESS, SELENIUM_WINDOW_SIZE # 절대 경로 임포트로 변경

def check_and_disable_coupons():
    print("[쿠폰 자동화] 기존 쿠폰 비활성화 시도 중...")
    options = Options()
    if SELENIUM_HEADLESS:
        options.add_argument('--headless')
    options.add_argument(f'--window-size={SELENIUM_WINDOW_SIZE}')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://wing.coupang.com/login")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(COUPANG_ID)
        driver.find_element(By.ID, "password").send_keys(COUPANG_PW)
        driver.find_element(By.ID, "kc-login").click()
        time.sleep(3)

        driver.get("https://wing.coupang.com/tenants/seller-promotion-platform/v2/seller-funding-coupon/coupons")
        time.sleep(3)

        try:
            close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".n-dialog__action button"))
            )
            close_btn.click()
            time.sleep(1)
        except:
            pass

        for attempt in range(3):
            rows = driver.find_elements(By.CSS_SELECTOR, "tr")
            print(f"행 발견: {len(rows)}개 (시도 {attempt + 1})")

            checked_any_coupon = False
            for idx, row in enumerate(rows[1:], 1):
                try:
                    status_cell = row.find_element(By.CSS_SELECTOR, "td[data-col-key='status']")
                    status = status_cell.text.strip()
                    if status == "사용중":
                        checkbox = row.find_element(By.CSS_SELECTOR, "div.n-checkbox")
                        driver.execute_script("arguments[0].click()", checkbox)
                        print(f"쿠폰 체크박스 클릭 완료 (행 {idx})")
                        checked_any_coupon = True
                        time.sleep(0.5)
                except Exception as e:
                    print(f"행 {idx} 처리 중 실패: {e}")

            if not checked_any_coupon:
                print("비활성화할 '사용중' 쿠폰이 없습니다.")
                break

            try:
                discard_btn = driver.find_element(By.XPATH, "//button[text()='사용중지']")
                if discard_btn.get_attribute("disabled"):
                    print("사용중지 버튼이 비활성화 상태입니다. (모든 쿠폰이 비활성화되었거나 선택된 쿠폰 없음)")
                    break
                discard_btn.click()
                print("사용중지 버튼 클릭 완료")
                time.sleep(1)

                for _ in range(2):
                    try:
                        confirm = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//span[text()='확인하다']/ancestor::button"))
                        )
                        confirm.click()
                        time.sleep(1)
                    except:
                        pass

                driver.refresh()
                time.sleep(3)
                print("쿠폰 비활성화 및 페이지 새로고침 완료.")

            except Exception as e:
                print(f"사용중지 버튼 클릭 또는 확인 실패: {e}")
                driver.save_screenshot("사용중지_실패.png")
                break
    except Exception as e:
        print(f"쿠폰 비활성화 전역 오류: {e}")
        driver.save_screenshot("비활성화_전역_오류.png")
    finally:
        driver.quit()