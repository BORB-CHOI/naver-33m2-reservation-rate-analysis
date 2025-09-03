import requests
import json
import time
import random
import pandas as pd
from datetime import datetime
import itertools


class NaverRealEstateCrawler:
    def __init__(self):
        self.base_url = "https://m.land.naver.com/cluster/ajax/articleList"

        # 다양한 User-Agent 회전
        self.user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; SM-A505F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Mobile/15E148 Safari/604.1",
        ]

        # 최신 URL 파라미터로 업데이트
        self.params = {
            "itemId": "",
            "mapKey": "",
            "lgeo": "",
            "showR0": "",
            "rletTpCd": "APT:OPST:OR",  # 아파트 + 원룸/오피스텔
            "tradTpCd": "B2",  # 월세
            "z": "12",
            "lat": "37.545181",
            "lon": "127.022949",
            "btm": "36.8",  # 수정된 좌표
            "lft": "126.60",
            "top": "38.3",
            "rgt": "127.35",
            "wprcMax": "1000",  # 보증금 최대 1000만원
            "spcMax": "99",  # 전용면적 최대 99㎡
            "sort": "rank",
        }

        # 세션 설정
        self.session = requests.Session()

    def get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Referer": "https://m.land.naver.com/map",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    def extract_property_info(self, property_data):
        """매물 정보 추출 및 가공"""
        try:
            info = {
                # ── 기존 필드 ───────────────────────────────────
                "매물제목": property_data.get("atclNm", "N/A"),
                "층수정보": property_data.get("flrInfo", "N/A"),
                "위도": property_data.get("lat", ""),
                "경도": property_data.get("lng", ""),
                "보증금": property_data.get("prc", "N/A"),
                "월세": property_data.get("rentPrc", "N/A"),
                "매물ID": property_data.get("atclNo", ""),
                "동일주소매물수": property_data.get("sameAddrCnt", 0),
                "전용면적": property_data.get("spc2", "N/A"),
                "주소": property_data.get("cortarNm", "N/A"),

                # ── 추가 요청 필드 ──────────────────────────────
                "매물유형": property_data.get("rletTpNm", "N/A"),        # 오피스텔, 아파트 등
                "방향": property_data.get("direction", "N/A"),          # 남향, 동향 등
                "건물명": property_data.get("bildNm", "N/A"),           # 102동, 103동 등
                "중개사무소명": property_data.get("cpNm", "N/A"),       # 이실장플러스 등
                "공인중개사": property_data.get("rltrNm", "N/A"),       # 하이공인중개사사무소 등
                "특징설명": property_data.get("atclFetrDesc", "N/A"),   # 신축·역세권 등
            }

            # 동일 주소 매물이 2개 이상이면 최대/최소 가격 정보 추가
            if property_data.get("sameAddrCnt", 0) >= 2:
                info.update(
                    {
                        "동일주소_최대보증금": property_data.get("sameAddrMaxPrc", "N/A"),
                        "동일주소_최대월세": property_data.get("sameAddrMaxPrc2", "N/A"),
                        "동일주소_최소보증금": property_data.get("sameAddrMinPrc", "N/A"),
                        "동일주소_최소월세": property_data.get("sameAddrMinPrc2", "N/A"),
                    }
                )
            else:
                info.update(
                    {
                        "동일주소_최대보증금": "",
                        "동일주소_최대월세": "",
                        "동일주소_최소보증금": "",
                        "동일주소_최소월세": "",
                    }
                )

            return info

        except Exception as e:
            print(f"⚠️ 매물 정보 추출 오류: {e}")
            return None

    def fetch_page(self, page):
        """단일 페이지 데이터 가져오기 - 안전한 순차 처리"""
        params = {**self.params, "page": page}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 요청 전 랜덤 딜레이 (중요!)
                delay = random.uniform(1.5, 3.0)
                time.sleep(delay)

                response = self.session.get(
                    self.base_url, params=params, headers=self.get_headers(), timeout=15
                )

                # 상태 코드 체크
                if response.status_code == 429:
                    wait_time = random.uniform(10, 20)
                    print(f"⚠️ Rate limit! Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue

                if response.status_code == 403:
                    wait_time = random.uniform(5, 10)
                    print(f"⚠️ Forbidden! Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    print(f"⚠️ Page {page} HTTP {response.status_code}")
                    time.sleep(random.uniform(2, 5))
                    continue

                # JSON 파싱
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    print(f"⚠️ Page {page} JSON 파싱 실패")
                    time.sleep(random.uniform(2, 4))
                    continue

                properties = data.get("body", [])

                # 빈 데이터면 종료 신호
                if not properties:
                    print(f"🏁 Page {page}: 데이터 없음 (크롤링 완료)")
                    return None  # None 반환으로 종료 신호

                # 데이터 가공
                processed_properties = []
                for prop in properties:
                    processed_prop = self.extract_property_info(prop)
                    if processed_prop:
                        processed_properties.append(processed_prop)

                print(f"✅ Page {page}: {len(processed_properties)}개 매물")
                return processed_properties

            except requests.RequestException as e:
                print(f"❌ Page {page} 네트워크 오류 (시도 {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = random.uniform(3, 8)
                    time.sleep(wait_time)
                    continue
            except Exception as e:
                print(f"❌ Page {page} 예외 (시도 {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 5))
                    continue

        print(f"💥 Page {page} 최대 재시도 초과")
        return []  # 빈 리스트 반환

    def crawl_safe_sequential(self):
        """안전한 순차 크롤링 - 무한루프 방식으로 빈 데이터까지"""
        all_properties = []
        failed_pages = []

        print("🏠 안전한 순차 크롤링 시작 (빈 데이터까지 자동 수집)")
        print("⚠️ 차단 방지를 위해 페이지당 1.5-3초 대기")

        start_time = time.time()
        page = 1

        while True:  # 무한 루프로 변경
            properties = self.fetch_page(page)

            # None이면 데이터 끝 (정상 종료)
            if properties is None:
                print(f"🎯 Page {page}에서 정상 종료")
                break

            # 빈 리스트면 실패한 페이지
            if not properties:
                failed_pages.append(page)
                print(f"⚠️ Page {page} 실패 - 나중에 재시도")
                page += 1
                continue

            all_properties.extend(properties)

            # 진행률 표시 (매 50페이지마다)
            if page % 50 == 0:
                elapsed = time.time() - start_time
                rate = len(all_properties) / (elapsed / 60) if elapsed > 0 else 0
                print(f"🔄 진행률: {page}페이지 완료")
                print(f"📊 수집: {len(all_properties)}개 ({rate:.1f}개/분)")

                # 중간 저장
                self.save_csv(all_properties, f"temp_{page}")

            page += 1

        # 실패한 페이지 재시도
        if failed_pages:
            print(f"\n🔄 실패한 페이지 재시도: {len(failed_pages)}개")
            for page in failed_pages[:10]:  # 최대 10개만 재시도
                print(f"🔄 재시도: Page {page}")
                properties = self.fetch_page(page)
                if properties and len(properties) > 0:
                    all_properties.extend(properties)
                    print(f"✅ 재시도 성공: {len(properties)}개")
                time.sleep(random.uniform(3, 6))

        return all_properties

    def save_csv(self, properties, filename_suffix=""):
        """CSV 파일 저장"""
        if not properties:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"naver_properties_{timestamp}"
        if filename_suffix:
            filename += f"_{filename_suffix}"
        filename += ".csv"

        try:
            df = pd.DataFrame(properties)
            df.to_csv(filename, index=False, encoding="utf-8-sig")

            # 통계 정보
            multi_addr = len(df[df["동일주소매물수"] >= 2])
            print(f"💾 저장완료: {filename}")
            print(f"📊 총 {len(properties)}개 (동일주소복수: {multi_addr}개)")

            return filename
        except Exception as e:
            print(f"❌저장 오류: {e}")
            return None


# 실행 코드
if __name__ == "__main__":
    crawler = NaverRealEstateCrawler()

    print("🏠 네이버 부동산 안전 크롤링 (순차 처리)")
    print("=" * 60)

    # 실행 확인
    choice = input("전체 크롤링을 시작하시겠습니까? (y/n): ").lower()
    if choice != "y":
        print("크롤링 취소됨")
        exit()

    start_time = time.time()

    # 안전한 순차 크롤링 실행 - max_page 파라미터 제거
    properties = crawler.crawl_safe_sequential()

    end_time = time.time()
    elapsed_time = end_time - start_time

    print("\n" + "=" * 60)
    print(f"🎉 크롤링 완료!")
    print(f"📊 총 수집 매물: {len(properties)}개")
    print(f"⏱️ 소요 시간: {elapsed_time/60:.1f}분")
    if len(properties) > 0:
        print(f"🚀 평균 속도: {len(properties)/(elapsed_time/60):.1f}개/분")

    # 최종 저장
    final_file = crawler.save_csv(properties, "final")

    # 샘플 데이터 출력
    if properties:
        print(f"\n📋 샘플 데이터 (처음 3개):")
        for i, prop in enumerate(properties[:3], 1):
            print(f"\n[{i}] {prop.get('매물제목', 'N/A')}")
            print(
                f"    💰 보증금/월세: {prop.get('보증금', 'N/A')}/{prop.get('월세', 'N/A')}"
            )
            print(
                f"    🏢 {prop.get('층수정보', 'N/A')} | 📐 {prop.get('전용면적', 'N/A')}㎡"
            )
            print(f"    📍 {prop.get('주소', 'N/A')}")
            if prop.get("동일주소매물수", 0) >= 2:
                print(
                    f"    📊 동일주소범위: {prop.get('동일주소_최소보증금', '')}-{prop.get('동일주소_최대보증금', '')}"
                )
