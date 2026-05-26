import os
import sys
import time
from datetime import datetime, timedelta

import requests as _req
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tabulate import tabulate

from report import build_markdown_report, build_dooray_message, build_html_report
from report.dooray import send_to_dooray
from config import get_dooray_config

load_dotenv()

BASE_URL = "https://dreamadmin.onuri.co.kr"
MAIN_URL = f"{BASE_URL}/main/mainView.do"

USERNAME = os.getenv("ADMIN_USER", "")
PASSWORD = os.getenv("ADMIN_PASS", "")
USER_FIELD = os.getenv("LOGIN_USER_FIELD", "")
PASS_FIELD = os.getenv("LOGIN_PASS_FIELD", "")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "reports")

# 자동 탐지 순서 (env 미지정 시)
_USER_CANDIDATES = ["loginId", "userId", "adminId", "id", "username"]
_PASS_CANDIDATES = ["loginPw", "userPwd", "adminPw", "pw", "password"]


def setup_driver(headless: bool = True) -> webdriver.Chrome:
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=ko-KR")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def find_field(driver, candidates: list[str]):
    for name in candidates:
        try:
            return driver.find_element(By.NAME, name)
        except NoSuchElementException:
            continue
    return None


def dismiss_alert(driver: webdriver.Chrome) -> None:
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except Exception:
        pass


def do_login(driver: webdriver.Chrome, wait: WebDriverWait, debug: bool = False) -> None:
    driver.get(MAIN_URL)
    time.sleep(2)
    dismiss_alert(driver)  # "세션이 종료 되었습니다." 등 팝업 처리

    if debug:
        print(f"[디버그] 현재 URL: {driver.current_url}")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"[디버그] 발견된 input 필드:")
        for inp in inputs:
            print(f"  type={inp.get_attribute('type')!r:10}  name={inp.get_attribute('name')!r:20}  id={inp.get_attribute('id')!r}")

    if "mainView" in driver.current_url:
        return

    user_field = (
        driver.find_element(By.NAME, USER_FIELD) if USER_FIELD
        else find_field(driver, _USER_CANDIDATES)
    )
    pass_field = (
        driver.find_element(By.NAME, PASS_FIELD) if PASS_FIELD
        else find_field(driver, _PASS_CANDIDATES)
    )

    if not user_field or not pass_field:
        raise RuntimeError(
            "로그인 폼 필드를 찾지 못했습니다.\n"
            ".env에 LOGIN_USER_FIELD, LOGIN_PASS_FIELD를 직접 지정하세요."
        )

    if debug:
        print(f"[디버그] 사용할 필드: user={user_field.get_attribute('name')!r}, pass={pass_field.get_attribute('name')!r}")

    user_field.clear()
    user_field.send_keys(USERNAME)
    pass_field.clear()
    pass_field.send_keys(PASSWORD)

    # 로그인 버튼 클릭 — CSS 셀렉터 → XPath 텍스트 순으로 탐색
    submit_btn = None
    css_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button.btnLogin",
        "a.btnLogin",
        ".btn-login",
    ]
    for selector in css_selectors:
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, selector)
            break
        except NoSuchElementException:
            continue

    if not submit_btn:
        xpath_candidates = [
            "//button[contains(., '로그인')]",
            "//a[contains(., '로그인')]",
            "//input[@type='button' and contains(@value, '로그인')]",
            "//button",  # 최후 수단: 페이지 첫 번째 button
        ]
        for xp in xpath_candidates:
            try:
                submit_btn = driver.find_element(By.XPATH, xp)
                break
            except NoSuchElementException:
                continue

    if submit_btn:
        if debug:
            print(f"[디버그] 버튼 클릭: <{submit_btn.tag_name}> text={submit_btn.text!r}")
        submit_btn.click()
    else:
        if debug:
            print("[디버그] 버튼을 못 찾아 form.submit() 사용")
        pass_field.submit()

    time.sleep(2)
    dismiss_alert(driver)

    if debug:
        print(f"[디버그] 제출 후 URL: {driver.current_url}")
        print(f"[디버그] 페이지 제목: {driver.title}")
        # 페이지에 오류 메시지가 있으면 출력
        from bs4 import BeautifulSoup as _BS
        _soup = _BS(driver.page_source, "html.parser")
        for sel in [".error", ".msg-error", ".login-error", "#errMsg", ".alert"]:
            el = _soup.select_one(sel)
            if el and el.get_text(strip=True):
                print(f"[디버그] 오류 메시지 ({sel}): {el.get_text(strip=True)}")

    try:
        wait.until(EC.url_contains("mainView"))
    except TimeoutException:
        raise RuntimeError(
            f"로그인 실패.\n"
            f"현재 URL: {driver.current_url}\n"
            "아이디/비밀번호 또는 VPN 연결을 확인하세요."
        )


def _cookies(driver: webdriver.Chrome) -> dict:
    return {c["name"]: c["value"] for c in driver.get_cookies()}


def _api_headers() -> dict:
    return {"Referer": MAIN_URL, "X-Requested-With": "XMLHttpRequest"}


# ── Summary 테이블: requests로 API 직접 호출 ──────────────────────────────────

def fetch_summary_table(driver: webdriver.Chrome):
    resp = _req.post(
        f"{BASE_URL}/main/totalStatReportGrid.do",
        headers=_api_headers(),
        cookies=_cookies(driver),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    today = datetime.now()
    col_headers = ["구분"]
    for i in range(7, 0, -1):
        col_headers.append((today - timedelta(days=i)).strftime("%m/%d"))
    col_headers += ["금일", "전일 대비", "당월 누적"]

    keys = ["name", "d7Total", "d6Total", "d5Total", "d4Total", "d3Total",
            "d2Total", "d1Total", "d0Total", "dbTotal", "daTotal"]
    rows = [[str(row.get(k, "")) for k in keys] for row in data.get("rows", [])]
    return col_headers, rows



def _parse_ul_from_soup(soup, ul_id: str) -> list[tuple[str, str]]:
    ul = soup.select_one(f"#{ul_id}")
    if not ul:
        return []
    result = []
    for li in ul.select("li"):
        num = li.select_one(".listNum")
        anc = li.select_one(".anc")
        if num and anc:
            result.append((num.get_text(strip=True), anc.get_text(strip=True)))
    return result


def _selenium_read_list(driver: webdriver.Chrome, css: str) -> list[tuple[str, str]]:
    items = driver.find_elements(By.CSS_SELECTOR, css)
    result = []
    for li in items:
        try:
            num = li.find_element(By.CLASS_NAME, "listNum").text.strip()
            anc = li.find_element(By.CLASS_NAME, "anc").text.strip()
            if num and anc:
                result.append((num, anc))
        except NoSuchElementException:
            continue
    return result


def fetch_lists_from_page(driver: webdriver.Chrome, debug: bool = False) -> tuple[list, list]:
    # API를 직접 호출하여 데이터 수집
    top5 = []
    top10 = []

    try:
        # TOP 5 상품 (getGoodsSearchTop10.do)
        resp_goods = _req.get(
            f"{BASE_URL}/main/getGoodsSearchTop10.do",
            headers=_api_headers(),
            cookies=_cookies(driver),
            timeout=15,
        )
        resp_goods.raise_for_status()
        goods_data = resp_goods.json()

        # goods_data에서 realTimeList 추출
        if isinstance(goods_data, dict) and "realTimeList" in goods_data:
            real_time_list = goods_data["realTimeList"]
            for idx, item in enumerate(real_time_list[:5], 1):  # 최대 5개만
                goods_name = item.get("goodsInfoStr", "")
                if goods_name:
                    top5.append((str(idx), goods_name))

        if debug:
            print(f"[디버그] getGoodsSearchTop10.do → {len(top5)}개 파싱")

    except Exception as e:
        if debug:
            print(f"[디버그] getGoodsSearchTop10.do 실패: {e}")

    try:
        # TOP 10 검색키워드 (getTrendkeywordsBo.do)
        resp_keywords = _req.get(
            f"{BASE_URL}/main/getTrendkeywordsBo.do",
            headers=_api_headers(),
            cookies=_cookies(driver),
            timeout=15,
        )
        resp_keywords.raise_for_status()
        keywords_data = resp_keywords.json()

        # keywords_data에서 rankList 추출
        if isinstance(keywords_data, dict) and "rankList" in keywords_data:
            rank_list = keywords_data["rankList"]
            for idx, keyword in enumerate(rank_list[:10], 1):  # 최대 10개
                if keyword:
                    top10.append((str(idx), str(keyword)))

        if debug:
            print(f"[디버그] getTrendkeywordsBo.do → {len(top10)}개 파싱")

    except Exception as e:
        if debug:
            print(f"[디버그] getTrendkeywordsBo.do 실패: {e}")

    if debug:
        print(f"[디버그] 최종 결과 → top5={len(top5)}건, top10={len(top10)}건")

    return top5, top10




def save_report(markdown_text: str, html_text: str, dooray_text: str) -> dict:
    """모든 형식의 리포트를 저장하고 경로 반환"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    paths = {}

    # 마크다운
    md_fname = f"{timestamp}_report.md"
    md_fpath = os.path.join(OUTPUT_DIR, md_fname)
    with open(md_fpath, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    paths["markdown"] = md_fpath

    # HTML
    html_fname = f"{timestamp}_report.html"
    html_fpath = os.path.join(OUTPUT_DIR, html_fname)
    with open(html_fpath, "w", encoding="utf-8") as f:
        f.write(html_text)
    paths["html"] = html_fpath

    # 두레이
    dooray_fname = f"{timestamp}_dooray.txt"
    dooray_fpath = os.path.join(OUTPUT_DIR, dooray_fname)
    with open(dooray_fpath, "w", encoding="utf-8") as f:
        f.write(dooray_text)
    paths["dooray"] = dooray_fpath

    return paths


def main() -> None:
    if not USERNAME or not PASSWORD:
        print("오류: .env 파일에 ADMIN_USER와 ADMIN_PASS를 설정하세요.")
        sys.exit(1)

    debug = "--debug" in sys.argv
    headless = "--show" not in sys.argv  # --show 옵션으로 브라우저 창을 표시

    driver = setup_driver(headless=headless)
    wait = WebDriverWait(driver, 25)

    try:
        print("로그인 중...")
        do_login(driver, wait, debug=debug)
        # 페이지 DOM 로드 완료 대기 (API 호출에 필요한 세션 쿠키 확보)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(5)  # easyui 초기화 및 JS 함수 등록 대기

        print("Summary 데이터 수집 중...")
        headers, rows = fetch_summary_table(driver)

        print("상품/키워드 데이터 수집 중...")
        top5, top10 = fetch_lists_from_page(driver, debug=debug)

        # 리포트 생성
        markdown_report = build_markdown_report(headers, rows, top5, top10)
        html_report = build_html_report(headers, rows, top5, top10)
        dooray_message = build_dooray_message(headers, rows, top5, top10)

        # 콘솔에 두레이 메시지 출력
        print("\n" + "=" * 70)
        print("[두레이 메신저 발송 메시지]")
        print("=" * 70)
        print(dooray_message)
        print("=" * 70 + "\n")

        # 파일 저장
        paths = save_report(markdown_report, html_report, dooray_message)
        print("✅ 리포트 생성 완료:")
        print(f"  - 마크다운: {paths['markdown']}")
        print(f"  - HTML: {paths['html']}")
        print(f"  - 두레이: {paths['dooray']}")

        # 두레이로 발송
        dooray_config = get_dooray_config()
        if dooray_config and dooray_config.get("webhook_url"):
            print("\n📤 두레이 메신저로 발송 중...")
            success = send_to_dooray(
                dooray_message,
                dooray_config["webhook_url"],
                dooray_config.get("bot_name", "Admin 통계봇"),
            )
            if success:
                print("✅ 두레이 메신저 발송 완료!")
            else:
                print("❌ 두레이 메신저 발송 실패")
        else:
            print("\n⚠️ 두레이 설정이 없습니다. (config.yml 확인)")


    except RuntimeError as e:
        print(f"\n오류: {e}")
        sys.exit(1)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
