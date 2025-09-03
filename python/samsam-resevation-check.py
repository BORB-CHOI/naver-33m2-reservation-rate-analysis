#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
33m2 월별 예약률 분석기a
- 4주만 분석 (state 필드 포함, .env 관리)
- 입력 CSV의 모든 필드를 결과 CSV 헤더에 그대로 반영
"""
import time, random, os
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Set
import pandas as pd
import httpx
from dotenv import load_dotenv


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# .env 로드 --------------------------------------------------------------------
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
if not EMAIL or not PASSWORD:
    raise SystemExit("❌ .env 파일에 EMAIL, PASSWORD 를 설정하세요")


# 기본 설정 --------------------------------------------------------------------
BASE_URL = "https://33m2.co.kr"
LOGIN_URL = f"{BASE_URL}/webpc/login"
SCHEDULE_URL = f"{BASE_URL}/app/room/schedule"
CSV_INPUT_FILE = "deduplicated_samsam_room_data.csv"  # ← 변경됨
OUTPUT_FILE = "room_reservation_4week_detailed.csv"


RESERVED_STATUSES = {"disable", "booking"}
ROOM_DELAY_MIN, ROOM_DELAY_MAX = 0.2, 0.5
MONTH_DELAY_MIN, MONTH_DELAY_MAX = 0.07, 0.15
BATCH_SIZE = 30
START_INDEX = 9700  # 재시작 인덱스


# 헤더 후보 --------------------------------------------------------------------
BROWSER_HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "br, gzip, deflate",
        "Connection": "close",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "close",
        "Cache-Control": "no-cache",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        "Accept-Encoding": "br, gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-cache",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "br, gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-store",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
        "Cache-Control": "no-store",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
        "Accept-Encoding": "br, gzip, deflate",
        "Connection": "close",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "no-store",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ja;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "close",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "DNT": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Cache-Control": "no-store",
        "Origin": "https://33m2.co.kr",
        "Referer": "https://33m2.co.kr/webpc/search/map",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    },
]


# 유틸 함수 --------------------------------------------------------------------
def get_4week_date_range() -> Tuple[date, date, List[str], List[Tuple[int, int]]]:
    today = date.today()
    end_date = today + timedelta(days=27)  # 4주 = 28일
    dates = [
        (today + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((end_date - today).days + 1)
    ]
    months = []
    m = today.replace(day=1)
    while m <= end_date:
        months.append((m.year, m.month))
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    return today, end_date, dates, months


# 주요 클래스 ------------------------------------------------------------------
class StealthAnalyzer:
    def __init__(self):
        self.driver = None
        self.http = None
        self.session_cookie = ""
        self.req_total = self.req_fail = 0
        self.last_req = 0.0

    # -------- 브라우저 초기화 -------------
    def setup_browser(self) -> bool:
        opts = Options()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-logging")
        opts.add_argument("--log-level=3")
        opts.add_argument("--window-size=1366,768")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument(
            f"--user-agent={random.choice(BROWSER_HEADERS)['User-Agent']}"
        )

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=opts
            )
            self.driver.execute_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
                "Object.defineProperty(navigator,'languages',{get:()=>['ko-KR','ko','en']});"
            )
            return True
        except Exception as e:
            print("❌ Chrome 시작 실패:", e)
            return False

    # -------- 로그인 ---------------------
    def login(self) -> bool:
        self.driver.get(LOGIN_URL)
        time.sleep(random.uniform(1.0, 2.0))
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            ).send_keys(EMAIL)
            for c in PASSWORD:
                self.driver.find_element(By.ID, "password").send_keys(c)
                time.sleep(random.uniform(0.05, 0.15))
            self.driver.find_element(
                By.XPATH, "//button[contains(text(),'로그인')]"
            ).click()
            time.sleep(random.uniform(2.0, 3.0))
            return True
        except Exception as e:
            print("❌ 로그인 오류:", e)
            return False

    # -------- 세션 추출 ------------------
    def extract_session(self) -> bool:
        for ck in self.driver.get_cookies():
            if ck["name"] == "SESSION":
                self.session_cookie = ck["value"]
                break
        if not self.session_cookie:
            print("❌ SESSION 쿠키 미발견")
            return False
        # httpx 클라이언트
        self.http = httpx.Client(timeout=30.0, cookies={"SESSION": self.session_cookie})
        return True

    # -------- 레이트리밋 ------------------
    def _pace(self):
        now = time.time()
        if now - self.last_req < 0.2:
            time.sleep(0.2 - (now - self.last_req) + random.uniform(0.05, 0.15))
        self.last_req = time.time()

    # -------- 월간 스케줄 -----------------
    def fetch_month(self, rid: int, y: int, m: int) -> Set[str]:
        self._pace()
        hdr = random.choice(BROWSER_HEADERS) | {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"{BASE_URL}/room/detail/{rid}",
            "Origin": BASE_URL,
        }
        payload = {"rid": str(rid), "year": str(y), "month": f"{m:02d}"}
        self.req_total += 1
        try:
            r = self.http.post(SCHEDULE_URL, data=payload, headers=hdr)
            if r.status_code != 200:
                self.req_fail += 1
                return set()
            js = r.json()
            if js.get("error_code", 0) != 0:
                self.req_fail += 1
                return set()
            return {
                d["date"]
                for d in js.get("schedule_list", [])
                if d.get("status") in RESERVED_STATUSES
            }
        except Exception:
            self.req_fail += 1
            return set()

    # -------- 4주 분석 --------------------
    def analyze_room(self, row: Dict) -> Dict:
        rid = row["rid"]
        t0, t1, dates, months = get_4week_date_range()
        reserved = set()
        for y, m in months:
            reserved |= self.fetch_month(rid, y, m)
            time.sleep(random.uniform(MONTH_DELAY_MIN, MONTH_DELAY_MAX))
        occ = round(len([d for d in dates if d in reserved]) / len(dates) * 100, 2)
        result = row.copy()  # 원본 필드 모두 포함
        # 필드 누락 대비 default set
        result.setdefault("state", "")
        # 추가 분석 필드
        result.update(
            {
                "analysis_start_date": str(t0),
                "analysis_end_date": str(t1),
                "occupancy_rate_percent": occ,
                "total_reserved_days": len(reserved & set(dates)),
                "total_days_analyzed": len(dates),
                "months_analyzed": len(months),
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return result

    # -------- 정리 -----------------------
    def close(self):
        if self.http:
            self.http.close()
        if self.driver:
            self.driver.quit()


# 헬퍼 -------------------------------------------------------------------------
def load_rooms() -> List[Dict]:
    df = pd.read_csv(CSV_INPUT_FILE, dtype=str)  # 모든 필드 문자열로 우선 로드
    # 숫자형 필드는 후처리할 수도 있음
    return df.to_dict(orient="records")


def save_batch(df: pd.DataFrame, header: bool):
    mode = "w" if header else "a"
    df.to_csv(OUTPUT_FILE, mode=mode, header=header, index=False, encoding="utf-8-sig")


def progress(
    i: int, total: int, name: str, occ: float, res: int, tot: int, an: StealthAnalyzer
):
    pct = i / total * 100
    bar = "█" * int(30 * i / total) + "░" * (30 - int(30 * i / total))
    eta = (total - i) * (time.time() - start_ts) / i if i else 0
    hrs, rem = divmod(int(eta), 3600)
    mins, sec = divmod(rem, 60)
    print(
        f"\r🏠[{i:4d}/{total}] [{bar}] {pct:5.1f}% | ETA:{hrs:02d}:{mins:02d}:{sec:02d} | "
        f"{name[:25]:<25} | 4주:{occ:5.1f}%({res}/{tot}) | "
        f"요청:{an.req_total} 실패:{an.req_fail} 성공률:{(an.req_total-an.req_fail)/an.req_total*100 if an.req_total else 0:4.1f}%",
        end="",
        flush=True,
    )


# 메인 -------------------------------------------------------------------------
if __name__ == "__main__":
    print("🎯 33m2 4주 예약률 분석기 (전체 필드 & 헤더 포함)")
    rooms = load_rooms()
    total = len(rooms)
    print(f"📂 입력 CSV: {CSV_INPUT_FILE} | 방 수: {total:,}")
    analyzer = StealthAnalyzer()
    if (
        not analyzer.setup_browser()
        or not analyzer.login()
        or not analyzer.extract_session()
    ):
        analyzer.close()
        raise SystemExit("⛔ 초기화 실패")
    analyzer.driver.quit()

    results = []
    header_written = False
    start_ts = time.time()

    for idx, row in enumerate(rooms[START_INDEX:], START_INDEX + 1):
        try:
            res = analyzer.analyze_room(row)
            results.append(res)
            progress(
                idx,
                total,
                res["room_name"],
                res["occupancy_rate_percent"],
                res["total_reserved_days"],
                res["total_days_analyzed"],
                analyzer,
            )
            if len(results) >= BATCH_SIZE or idx == total:
                df = pd.DataFrame(results)
                # 첫 저장 때만 헤더
                save_batch(df, not header_written)
                header_written = True
                results.clear()
                print()  # 줄바꿈
            if idx < total:
                time.sleep(random.uniform(ROOM_DELAY_MIN, ROOM_DELAY_MAX))
        except KeyboardInterrupt:
            print("\n🛑 사용자 중단")
            break
        except Exception as e:
            print(f"\n❌ {row.get('room_name','Unknown')} 오류:{e}")
            continue

    analyzer.close()
    print(f"\n✅ 완료! 결과 파일 → {OUTPUT_FILE}")
