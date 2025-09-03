#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
33m2 수도권(서울/인천/경기) 오피스텔&아파트 크롤링 - 완전한 코드
실행: python metropolitan_crawler_complete.py
"""
import time, random, json
from datetime import datetime
from typing import Dict, List, Set, Tuple
import pandas as pd
import httpx


# ---- 설정 ----
SEARCH_URL = "https://33m2.co.kr/app/room/search"
OUTPUT_FILE = "metropolitan_officetel_complete.csv"

# 딜레이 설정 (차단 방지)
REQUEST_DELAY_MIN = 2.5
REQUEST_DELAY_MAX = 5
BATCH_SIZE = 100

# 수도권 전체 행정구역 (66개 기초자치단체)
METROPOLITAN_AREAS = {
    # 서울특별시 25개 자치구
    "서울특별시": [
        "강남구",
        "강동구",
        "강북구",
        "강서구",
        "관악구",
        "광진구",
        "구로구",
        "금천구",
        "노원구",
        "도봉구",
        "동대문구",
        "동작구",
        "마포구",
        "서대문구",
        "서초구",
        "성동구",
        "성북구",
        "송파구",
        "양천구",
        "영등포구",
        "용산구",
        "은평구",
        "종로구",
        "중구",
        "중랑구",
    ],
    # 인천광역시 8구 2군
    "인천광역시": [
        "중구",
        "동구",
        "미추홀구",
        "연수구",
        "남동구",
        "부평구",
        "계양구",
        "서구",
        "강화군",
        "옹진군",
    ],
    # 경기도 28시 3군
    "경기도": [
        "수원시",
        "성남시",
        "의정부시",
        "안양시",
        "부천시",
        "광명시",
        "평택시",
        "동두천시",
        "안산시",
        "고양시",
        "과천시",
        "구리시",
        "남양주시",
        "오산시",
        "시흥시",
        "군포시",
        "의왕시",
        "하남시",
        "용인시",
        "파주시",
        "이천시",
        "안성시",
        "김포시",
        "화성시",
        "광주시",
        "양주시",
        "포천시",
        "여주시",
        "연천군",
        "가평군",
        "양평군",
    ],
}

# 매물 밀집 지역별 세분화 (주요 도시만)
DISTRICT_SUBDIVISIONS = {
    "강남구": [
        "개포동",
        "논현동",
        "대치동",
        "도곡동",
        "삼성동",
        "세곡동",
        "신사동",
        "압구정동",
        "역삼동",
        "일원동",
        "청담동",
        "수서동",
        "율현동",
        "자곡동",
    ],
    "강동구": [
        "강일동",
        "고덕동",
        "길동",
        "둔촌동",
        "명일동",
        "상일동",
        "성내동",
        "암사동",
        "천호동",
        "둔촌제1동",
        "둔촌제2동",
    ],
    "강북구": ["미아동", "번동", "수유동", "우이동", "인수동"],
    "강서구": [
        "가양동",
        "개화동",
        "공항동",
        "과해동",
        "내발산동",
        "등촌동",
        "마곡동",
        "방화동",
        "염창동",
        "오곡동",
        "오쇠동",
        "외발산동",
        "화곡동",
    ],
    "관악구": [
        "낙성대동",
        "난곡동",
        "난향동",
        "남현동",
        "대학동",
        "미성동",
        "보라매동",
        "삼성동",
        "서림동",
        "서원동",
        "성현동",
        "신림동",
        "신사동",
        "신원동",
        "은천동",
        "조원동",
        "중앙동",
        "청룡동",
        "청림동",
        "행운동",
        "인헌동",
    ],
    "광진구": ["광장동", "군자동", "능동", "자양동", "중곡동", "화양동", "구의동"],
    "구로구": [
        "가리봉동",
        "개봉동",
        "고척동",
        "구로동",
        "궁동",
        "수궁동",
        "오류동",
        "온수동",
        "신도림동",
        "항동",
        "천왕동",
    ],
    "금천구": ["가산동", "독산동", "시흥동"],
    "노원구": ["공릉동", "상계동", "월계동", "중계동", "하계동"],
    "도봉구": ["방학동", "쌍문동", "도봉동", "창동"],
    "동대문구": [
        "답십리동",
        "장안동",
        "전농동",
        "제기동",
        "청량리동",
        "회기동",
        "휘경동",
        "이문동",
        "용두동",
        "신설동",
    ],
    "동작구": [
        "노량진동",
        "대방동",
        "동작동",
        "본동",
        "사당동",
        "상도동",
        "신대방동",
        "흑석동",
        "상도1동",
    ],
    "마포구": [
        "공덕동",
        "노고산동",
        "당인동",
        "도화동",
        "동교동",
        "동산동",
        "망원동",
        "상수동",
        "서교동",
        "신공덕동",
        "신수동",
        "아현동",
        "연남동",
        "염리동",
        "용강동",
        "중동",
        "창전동",
        "토정동",
        "합정동",
        "현석동",
        "성산동",
        "마포동",
        "대흥동",
        "구수동",
        "하중동",
        "상암동",
    ],
    "서대문구": [
        "남가좌동",
        "북가좌동",
        "북아현동",
        "신촌동",
        "연희동",
        "영천동",
        "옥천동",
        "천연동",
        "충정로동",
        "합동",
        "현저동",
        "홍은동",
        "홍제동",
        "대현동",
        "미근동",
        "대신동",
        "봉원동",
        "창천동",
        "냉천동",
        "옥천동",
    ],
    "서초구": [
        "내곡동",
        "논현동",
        "반포동",
        "방배동",
        "서초동",
        "신원동",
        "양재동",
        "염곡동",
        "우면동",
        "잠원동",
    ],
    "성동구": [
        "금호동1가",
        "금호동2가",
        "금호동3가",
        "금호동4가",
        "마장동",
        "사근동",
        "상왕십리동",
        "성수동1가",
        "성수동2가",
        "송정동",
        "옥수동",
        "용답동",
        "응봉동",
        "하왕십리동",
        "행당동",
        "왕십리도선동",
    ],
    "성북구": [
        "길음동",
        "돈암동",
        "동선동",
        "보문동",
        "삼선동",
        "상월곡동",
        "석관동",
        "안암동",
        "장위동",
        "정릉동",
        "종암동",
        "하월곡동",
        "성북동",
        "동소문동1가",
        "동소문동2가",
        "동소문동3가",
        "동소문동4가",
        "동소문동5가",
        "삼선동1가",
        "삼선동2가",
        "삼선동3가",
        "삼선동4가",
        "삼선동5가",
        "보문동1가",
        "보문동2가",
        "보문동3가",
        "보문동4가",
        "보문동5가",
        "보문동6가",
        "보문동7가",
    ],
    "송파구": [
        "가락동",
        "거여동",
        "마천동",
        "문정동",
        "방이동",
        "삼전동",
        "석촌동",
        "송파동",
        "신천동",
        "오금동",
        "오륜동",
        "위례동",
        "장지동",
        "잠실동",
        "풍납동",
    ],
    "양천구": ["목동", "신월동", "신정동"],
    "영등포구": [
        "당산동",
        "대림동",
        "도림동",
        "문래동",
        "양평동",
        "여의도동",
        "영등포동",
        "신길동",
    ],
    "용산구": [
        "갈월동",
        "남영동",
        "도원동",
        "동자동",
        "문배동",
        "보광동",
        "서계동",
        "서빙고동",
        "용문동",
        "용산동2가",
        "용산동3가",
        "용산동4가",
        "용산동5가",
        "원효로1가",
        "원효로2가",
        "이촌동",
        "이태원동",
        "청암동",
        "청파동1가",
        "청파동2가",
        "청파동3가",
        "한강로1가",
        "한강로2가",
        "한남동",
        "후암동",
        "용산동1가",
        "용산동6가",
        "한강로3가",
        "동빙고동",
        "주성동",
        "산천동",
        "신창동",
        "신계동",
        "원효로3가",
        "원효로4가",
        "효창동",
    ],
    "은평구": [
        "갈현동",
        "구산동",
        "녹번동",
        "대조동",
        "불광동",
        "수색동",
        "신사동",
        "역촌동",
        "응암동",
        "증산동",
        "진관동",
    ],
    "종로구": [
        "가회동",
        "견지동",
        "경운동",
        "계동",
        "공평동",
        "관수동",
        "관철동",
        "관훈동",
        "교남동",
        "교북동",
        "구기동",
        "궁정동",
        "권농동",
        "낙원동",
        "내수동",
        "내자동",
        "누상동",
        "누하동",
        "당주동",
        "도렴동",
        "돈의동",
        "동숭동",
        "명륜1가",
        "명륜2가",
        "명륜3가",
        "명륜4가",
        "묘동",
        "무악동",
        "봉익동",
        "부암동",
        "사간동",
        "사직동",
        "삼청동",
        "서린동",
        "세종로",
        "소격동",
        "송현동",
        "숭인동",
        "신교동",
        "신문로1가",
        "신문로2가",
        "신영동",
        "안국동",
        "연건동",
        "연지동",
        "예지동",
        "원남동",
        "익선동",
        "인사동",
        "인의동",
        "장사동",
        "재동",
        "적선동",
        "종로1가",
        "종로2가",
        "종로3가",
        "종로4가",
        "종로5가",
        "종로6가",
        "중학동",
        "창성동",
        "창신동",
        "청운동",
        "청진동",
        "충신동",
        "통의동",
        "통인동",
        "팔판동",
        "평동",
        "평창동",
        "필운동",
        "홍지동",
        "화동",
        "효자동",
        "효제동",
        "체부동",
        "내자동",
        "도렴동",
        "당주동",
        "내수동",
        "신문로1가",
        "신문로2가",
        "원서동",
        "수송동",
        "운니동",
        "와룡동",
        "훈정동",
    ],
    "중구": [
        "광희동1가",
        "광희동2가",
        "남대문로1가",
        "남대문로2가",
        "남대문로3가",
        "남대문로4가",
        "남대문로5가",
        "남산동1가",
        "남산동2가",
        "남산동3가",
        "남창동",
        "남학동",
        "다동",
        "만리동1가",
        "만리동2가",
        "명동1가",
        "명동2가",
        "무교동",
        "무학동",
        "방산동",
        "봉래동1가",
        "봉래동2가",
        "북창동",
        "산림동",
        "삼각동",
        "서소문동",
        "소공동",
        "수표동",
        "수하동",
        "순화동",
        "신당동",
        "쌍림동",
        "예관동",
        "오장동",
        "을지로1가",
        "을지로2가",
        "을지로3가",
        "을지로4가",
        "을지로5가",
        "을지로6가",
        "을지로7가",
        "의주로1가",
        "의주로2가",
        "인현동1가",
        "인현동2가",
        "입정동",
        "장교동",
        "저동1가",
        "저동2가",
        "정동",
        "주교동",
        "주자동",
        "중림동",
        "초동",
        "충무로1가",
        "충무로2가",
        "충무로3가",
        "충무로4가",
        "충무로5가",
        "태평로1가",
        "태평로2가",
        "필동1가",
        "필동2가",
        "필동3가",
        "황학동",
        "회현동1가",
        "회현동2가",
        "회현동3가",
        "태평로1가",
        "무학동",
        "흥인동",
        "인현동",
        "저동2가",
        "입정동",
    ],
    "중랑구": ["면목동", "묵동", "망우동", "상봉동", "중화동", "신내동"],
    "중구": ["신포동", "차이나타운동", "항동", "영종동", "운서동", "을왕동"],
    "동구": ["화수동", "송림동", "송현동"],
    "미추홀구": ["관교동", "주안동", "학익동", "도화동", "숭의동"],
    "연수구": ["동춘동", "연수동", "옥련동", "청학동", "송도동"],
    "남동구": ["구월동", "간석동", "만수동", "장수동", "서창동", "논현동"],
    "부평구": [
        "부평동",
        "십정동",
        "산곡동",
        "청천동",
        "갈산동",
        "삼산동",
        "부개동",
        "일신동",
    ],
    "계양구": ["계산동", "작전동", "효성동"],
    "서구": ["가정동", "석남동", "가좌동", "검단동", "청라동"],
    "강화군": ["강화읍", "선원면", "길상면", "하점면", "불은면"],
    "옹진군": ["영흥면", "덕적면", "대청면", "자월면", "연평면"],
    "수원시": {
        "장안구": [
            "파장동",
            "율전동",
            "정자동",
            "영화동",
            "송죽동",
            "조원동",
            "연무동",
        ],
        "권선구": [
            "세류동",
            "권선동",
            "곡선동",
            "구운동",
            "입북동",
            "서둔동",
            "고색동",
            "탑동",
            "평동",
            "대황교동",
        ],
        "팔달구": [
            "인계동",
            "매교동",
            "매산로동",
            "교동",
            "신풍동",
            "남수동",
            "남창동",
            "지동",
            "우만동",
            "화서동",
        ],
        "영통구": ["영통동", "망포동", "원천동", "이의동", "하동", "신동", "광교동"],
    },
    "성남시": {
        "수정구": [
            "수진동",
            "신흥동",
            "태평동",
            "상대원동",
            "단대동",
            "산성동",
            "양지동",
            "복정동",
            "창곡동",
        ],
        "중원구": [
            "성남동",
            "중앙동",
            "금광동",
            "은행동",
            "상대원동",
            "하대원동",
            "도촌동",
        ],
        "분당구": [
            "이매동",
            "야탑동",
            "정자동",
            "서현동",
            "수내동",
            "판교동",
            "삼평동",
            "운중동",
            "구미동",
            "금곡동",
            "동원동",
        ],
    },
    "의정부시": [
        "의정부동",
        "호원동",
        "장암동",
        "신곡동",
        "민락동",
        "가능동",
        "흥선동",
        "녹양동",
    ],
    "안양시": {
        "만안구": ["안양동", "석수동", "박달동"],
        "동안구": [
            "비산동",
            "관양동",
            "부흥동",
            "평촌동",
            "호계동",
            "범계동",
            "달안동",
            "귀인동",
        ],
    },
    "부천시": {
        "소사구": ["소사본동", "송내동", "심곡본동"],
        "오정구": ["원종동", "오정동", "작동", "고강동", "삼정동"],
        "원미구": [
            "중동",
            "상동",
            "여월동",
            "도당동",
            "춘의동",
            "심곡동",
            "소사동",
            "역곡동",
        ],
    },
    "광명시": [
        "광명동",
        "철산동",
        "하안동",
        "소하동",
        "일직동",
        "노온사동",
        "가학동",
        "옥길동",
    ],
    "평택시": [
        "평택동",
        "비전동",
        "통복동",
        "합정동",
        "서정동",
        "장당동",
        "동삭동",
        "용이동",
        "안중읍",
        "오성면",
        "청북읍",
        "포승읍",
        "고덕면",
        "진위면",
        "현덕면",
        "팽성읍",
    ],
    "동두천시": [
        "생연동",
        "송내동",
        "지행동",
        "동두천동",
        "상패동",
        "안흥동",
        "탑동동",
        "보산동",
    ],
    "안산시": {
        "상록구": [
            "일동",
            "이동",
            "본오동",
            "사동",
            "부곡동",
            "월피동",
            "성포동",
            "반월동",
            "수암동",
        ],
        "단원구": ["와동", "고잔동", "원곡동", "초지동", "선부동", "신길동", "대부동"],
    },
    "고양시": {
        "덕양구": [
            "주교동",
            "원신동",
            "성사동",
            "화정동",
            "행신동",
            "능곡동",
            "신도동",
            "삼송동",
            "지축동",
            "고양동",
            "관산동",
            "동산동",
        ],
        "일산동구": [
            "정발산동",
            "장항동",
            "백석동",
            "마두동",
            "식사동",
            "풍동",
            "중산동",
            "문봉동",
            "설문동",
        ],
        "일산서구": [
            "대화동",
            "송포동",
            "주엽동",
            "탄현동",
            "덕이동",
            "가좌동",
            "일산동",
        ],
    },
    "과천시": ["별양동", "부림동", "과천동", "주암동", "문원동"],
    "구리시": ["교문동", "수택동", "인창동", "토평동"],
    "남양주시": [
        "금곡동",
        "수석동",
        "호평동",
        "평내동",
        "오남읍",
        "화도읍",
        "진접읍",
        "와부읍",
        "별내동",
        "퇴계원읍",
        "조안면",
        "진건읍",
        "양정동",
        "다산동",
    ],
    "오산시": [
        "오산동",
        "원동",
        "벌음동",
        "외삼미동",
        "내삼미동",
        "세교동",
        "가장동",
        "금암동",
        "수청동",
        "청학동",
        "양산동",
    ],
    "시흥시": [
        "정왕동",
        "신천동",
        "대야동",
        "매화동",
        "은행동",
        "과림동",
        "목감동",
        "장곡동",
        "논곡동",
        "금이동",
        "미산동",
        "방산동",
        "배곧동",
    ],
    "군포시": ["당정동", "산본동", "금정동", "궁내동", "부곡동", "속달동", "대야미동"],
    "의왕시": ["고천동", "오전동", "왕곡동", "삼동", "청계동", "내손동", "포일동"],
    "하남시": [
        "천현동",
        "신장동",
        "덕풍동",
        "창우동",
        "감북동",
        "감일동",
        "위례동",
        "풍산동",
        "춘궁동",
        "하산곡동",
    ],
    "용인시": {
        "처인구": [
            "김량장동",
            "남동",
            "역북동",
            "삼가동",
            "동부동",
            "유방동",
            "운학동",
            "고림동",
            "마평동",
            "호동",
            "포곡읍",
            "모현읍",
            "이동읍",
            "백암면",
            "원삼면",
            "양지면",
        ],
        "기흥구": [
            "기흥동",
            "구갈동",
            "구성동",
            "동백동",
            "마북동",
            "상갈동",
            "상하동",
            "보라동",
            "신갈동",
            "영덕동",
            "중동",
            "서농동",
        ],
        "수지구": ["죽전동", "풍덕천동", "신봉동", "성복동", "동천동"],
    },
    "파주시": [
        "금촌동",
        "아동동",
        "야동동",
        "검산동",
        "맥금동",
        "교하동",
        "조리읍",
        "문산읍",
        "법원읍",
        "광탄면",
        "파평면",
        "적성면",
        "탄현면",
        "파주읍",
        "장단면",
        "월롱면",
        "군내면",
        "장파면",
    ],
    "이천시": [
        "관고동",
        "중리동",
        "증포동",
        "창전동",
        "신둔면",
        "백사면",
        "마장면",
        "부발읍",
        "대월면",
        "호법면",
        "모가면",
        "설성면",
        "율면",
    ],
    "안성시": [
        "봉산동",
        "옥산동",
        "인지동",
        "계동",
        "사곡동",
        "금석동",
        "당왕동",
        "구포동",
        "안성동",
        "석정동",
        "신건지동",
        "대천동",
        "옥천동",
        "현수동",
        "발화동",
        "아양동",
        "연지동",
        "현매동",
        "양성면",
        "원곡면",
        "보개면",
        "일죽면",
        "죽산면",
        "삼죽면",
        "고삼면",
        "금광면",
        "서운면",
        "미양면",
        "대덕면",
    ],
    "김포시": [
        "북변동",
        "걸포동",
        "감정동",
        "장기동",
        "사우동",
        "풍무동",
        "통진읍",
        "고촌읍",
        "양촌읍",
        "대곶면",
        "월곶면",
        "하성면",
    ],
    "화성시": [
        "진안동",
        "병점동",
        "반월동",
        "기산동",
        "진안동",
        "안녕동",
        "반송동",
        "석우동",
        "마도면",
        "송산면",
        "서신면",
        "팔탄면",
        "향남읍",
        "정남면",
        "우정읍",
        "남양읍",
        "비봉면",
        "장안면",
        "양감면",
        "장지동",
        "영천동",
        "송동",
        "동탄면",
        "동탄동",
    ],
    "광주시": [
        "경안동",
        "송정동",
        "쌍령동",
        "목동",
        "삼동",
        "탄벌동",
        "장지동",
        "중대동",
        "회덕동",
        "직동",
        "양벌동",
        "장지동",
        "도척면",
        "남종면",
        "남한산성면",
        "남종면",
        "초월읍",
        "곤지암읍",
        "퇴촌면",
        "오포읍",
    ],
    "양주시": [
        "남방동",
        "남면",
        "남외동",
        "능암동",
        "덕계동",
        "만송동",
        "백석읍",
        "삼숭동",
        "유양동",
        "은현면",
        "장흥면",
        "고암동",
        "광사동",
        "회암동",
        "고읍동",
        "덕정동",
    ],
    "포천시": [
        "관인면",
        "군내면",
        "내촌면",
        "동교동",
        "선단동",
        "설운동",
        "신읍동",
        "자작동",
        "신북면",
        "영북면",
        "영중면",
        "일동면",
        "이동면",
        "창수면",
        "화현면",
        "소흘읍",
        "포천동",
    ],
    "여주시": [
        "가남읍",
        "강천면",
        "금사면",
        "능서면",
        "대신면",
        "산북면",
        "점동면",
        "오학동",
        "여흥동",
        "홍문동",
        "흥천면",
    ],
    "연천군": [
        "전곡읍",
        "연천읍",
        "군남면",
        "백학면",
        "미산면",
        "왕징면",
        "장남면",
        "청산면",
        "신서면",
        "중면",
        "백의면",
    ],
    "가평군": ["가평읍", "설악면", "청평면", "상면", "조종면", "북면"],
    "양평군": [
        "양평읍",
        "강상면",
        "강하면",
        "개군면",
        "단월면",
        "서종면",
        "양동면",
        "옥천면",
        "용문면",
        "지평면",
        "청운면",
    ],
}

# 고정 좌표 (대한민국 전체)
COORDINATES = {
  "north_east_lng": "131.900000",
  "north_east_lat": "43.000000",
  "south_west_lng": "124.610058", 
  "south_west_lat": "32.000000",
}

# User Agent 풀 (차단 방지)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

class MetropolitanCrawler:
    def __init__(self):
        self.http_client = httpx.Client(timeout=30.0)
        self.all_fields_discovered = set()
        self.failed_areas = []
        self.total_processed = 0

    def get_random_headers(self) -> Dict[str, str]:
        """랜덤 헤더 생성 (차단 방지)"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": random.choice(
                ["ko-KR,ko;q=0.9,en;q=0.8", "ko,en-US;q=0.9,en;q=0.8"]
            ),
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://33m2.co.kr",
            "Referer": "https://33m2.co.kr/webpc/search/map",
            "Cache-Control": "no-cache",
        }

    def adaptive_delay(self, region_type: str = "normal"):
        """지역 타입에 따른 적응형 딜레이"""
        if region_type == "seoul":
            delay = random.uniform(REQUEST_DELAY_MIN + 0.5, REQUEST_DELAY_MAX + 1.0)
        elif region_type == "incheon":
            delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX + 0.5)
        else:  # gyeonggi
            delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)

        print(f"    💤 {delay:.1f}초 대기 중...", end="", flush=True)
        time.sleep(delay)
        print(" ✓")

    def discover_fields(self, rooms: List[Dict]) -> Set[str]:
        """응답 데이터에서 모든 필드 발견"""
        discovered_fields = set()

        for room in rooms:
            if isinstance(room, dict):
                for key in room.keys():
                    discovered_fields.add(key)

                try:
                    flattened = pd.json_normalize([room])
                    for col in flattened.columns:
                        discovered_fields.add(col)
                except:
                    pass

        return discovered_fields

    def flatten_room_data(self, room: Dict) -> Dict:
        """방 데이터를 평면화 (모든 중첩 필드 포함)"""
        try:
            flattened_df = pd.json_normalize([room])

            if len(flattened_df) > 0:
                flattened_dict = flattened_df.iloc[0].to_dict()

                # 크롤링 메타데이터 추가
                flattened_dict["crawl_datetime"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                flattened_dict["crawl_timestamp"] = int(datetime.now().timestamp())

                return flattened_dict
            else:
                return room
        except Exception as e:
            print(f"    ⚠️ 데이터 평면화 실패: {e}")
            return room

    def fetch_area_rooms(self, keyword: str, region_type: str = "normal") -> List[Dict]:
        """지역별 오피스텔&아파트 매물 수집"""
        self.http_client.headers.update(self.get_random_headers())

        payload = {
            "keyword": keyword,
            "by_location": "true",
            "north_east_lng": COORDINATES["north_east_lng"],
            "north_east_lat": COORDINATES["north_east_lat"],
            "south_west_lng": COORDINATES["south_west_lng"],
            "south_west_lat": COORDINATES["south_west_lat"],
            "itemcount": "1000",
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.http_client.post(SEARCH_URL, data=payload)

                if response.status_code == 403:
                    print(
                        f"    🚫 403 차단 - 헤더 변경 후 재시도 ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(random.uniform(5.0, 10.0))
                    self.http_client.headers.update(self.get_random_headers())
                    continue

                response.raise_for_status()
                result = response.json()

                if result.get("error_code", 0) == 0 and "list" in result:
                    rooms = result["list"]
                    print(f"    ✅ {keyword}: {len(rooms)}개 매물 수집")

                    # 필드 발견 및 추적
                    discovered_fields = self.discover_fields(rooms)
                    new_fields = discovered_fields - self.all_fields_discovered
                    self.all_fields_discovered.update(discovered_fields)

                    if new_fields:
                        print(f"    🆕 새 필드 발견: {', '.join(list(new_fields)[:3])}")

                    if len(rooms) >= 1000:
                        print(f"    ⚠️  {keyword}: 1000개 도달 - 세분화 권장")

                    return rooms
                else:
                    print(
                        f"    ❌ {keyword}: API 오류 (error_code: {result.get('error_code')})"
                    )
                    return []

            except Exception as e:
                print(
                    f"    ❌ {keyword}: 요청 실패 (시도 {attempt + 1}/{max_retries}) - {str(e)[:50]}"
                )
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3.0, 6.0))
                continue

        # 모든 재시도 실패
        self.failed_areas.append(keyword)
        return []

    def process_area_with_subdivision(self, area: str, region_name: str) -> List[Dict]:
        """지역별 처리 (필요시 세분화)"""
        region_type = (
            "seoul"
            if region_name == "서울특별시"
            else ("incheon" if region_name == "인천광역시" else "gyeonggi")
        )
        print(f"\n🏢 {region_name} {area} 처리 중...")

        # 먼저 지역 단위로 시도
        area_rooms = self.fetch_area_rooms(area, region_type)

        # 1000개 미만이면 그대로 반환
        if len(area_rooms) < 1000:
            processed_rooms = []
            for room in area_rooms:
                flattened_room = self.flatten_room_data(room)
                flattened_room["search_keyword"] = area
                flattened_room["region_name"] = region_name
                processed_rooms.append(flattened_room)
            return processed_rooms

        # 1000개 이상이면 세분화
        print(f"  🔄 {area} 세분화 시작...")
        all_rooms = []

        if area in DISTRICT_SUBDIVISIONS:
            subdivisions = DISTRICT_SUBDIVISIONS[area]

            for subdivision in subdivisions:
                sub_keyword = f"{area} {subdivision}"
                sub_rooms = self.fetch_area_rooms(sub_keyword, region_type)

                for room in sub_rooms:
                    flattened_room = self.flatten_room_data(room)
                    flattened_room["search_keyword"] = sub_keyword
                    flattened_room["region_name"] = region_name
                    all_rooms.append(flattened_room)

                # 세분화 간 딜레이
                self.adaptive_delay(region_type)
        else:
            print(f"    ⚠️  {area} 세분화 정보 없음 - 원본 데이터 사용")
            for room in area_rooms:
                flattened_room = self.flatten_room_data(room)
                flattened_room["search_keyword"] = area
                flattened_room["region_name"] = region_name
                all_rooms.append(flattened_room)

        # 중복 제거 (rid 기준)
        unique_rooms = {}
        for room in all_rooms:
            rid = room.get("rid")
            if rid and rid not in unique_rooms:
                unique_rooms[rid] = room

        final_rooms = list(unique_rooms.values())
        print(f"  ✅ {area} 최종: {len(final_rooms)}개 (중복 제거)")
        return final_rooms

    def close(self):
        """리소스 정리"""
        try:
            if self.http_client:
                self.http_client.close()
        except:
            pass


def save_results_complete(all_rooms: List[Dict]):
    """완전한 결과 저장"""
    try:
        if not all_rooms:
            print("❌ 저장할 데이터 없음")
            return

        df = pd.json_normalize(all_rooms)

        print(f"📊 발견된 총 필드 수: {len(df.columns)}개")
        print(f"📋 주요 필드: {list(df.columns)[:8]}...")

        # CSV 저장
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

        print(f"💾 저장 완료: {OUTPUT_FILE}")
        print(f"📊 총 매물: {len(all_rooms):,}개")
        print(f"📋 총 컬럼: {len(df.columns)}개")

        # 지역별 통계
        if "region_name" in df.columns:
            region_stats = df["region_name"].value_counts()
            print(f"\n📈 지역별 매물 수:")
            for region, count in region_stats.items():
                print(f"  📍 {region}: {count:,}개")

        # 샘플 데이터 미리보기
        if len(df) > 0:
            print(f"\n📋 샘플 데이터:")
            sample_cols = [
                "rid",
                "room_name",
                "province",
                "town",
                "using_fee",
                "pyeong_size",
                "region_name",
            ]
            available_sample_cols = [col for col in sample_cols if col in df.columns]
            if available_sample_cols:
                print(df[available_sample_cols].head(3).to_string(index=False))

    except Exception as e:
        print(f"❌ 저장 실패: {e}")
        import traceback

        traceback.print_exc()


def print_progress(
    current: int,
    total: int,
    area: str,
    room_count: int,
    elapsed_time: float,
    region: str,
):
    """진행률 표시"""
    percentage = (current / total) * 100
    bar_length = 30
    filled_length = int(bar_length * current // total)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)

    if current > 0:
        avg_time = elapsed_time / current
        eta = (total - current) * avg_time
        eta_str = f"{int(eta//60):02d}:{int(eta%60):02d}"
    else:
        eta_str = "00:00"

    print(
        f"\r🏙️ [{current:2d}/{total}] [{bar}] {percentage:5.1f}% | ETA: {eta_str} | {region[:2]} {area:<8} | {room_count:4d}개",
        end="",
        flush=True,
    )


def main():
    """메인 실행"""
    print("🚀 33m2 수도권 전체 오피스텔&아파트 크롤링 - 완전판")
    print(f"🎯 대상: 수도권 66개 기초자치단체 (서울25 + 인천10 + 경기31)")
    print(f"🏢 매물 타입: 오피스텔, 아파트")
    print(f"⏱️ 딜레이: 지역별 적응형 ({REQUEST_DELAY_MIN}~{REQUEST_DELAY_MAX}초)")
    print(f"🛡️ 차단 방지: User-Agent 로테이션 + 실패 복구")
    print(f"📊 데이터: API 응답의 모든 필드 자동 저장 + 지역 메타데이터")
    print("=" * 80)

    crawler = MetropolitanCrawler()
    start_time = time.time()

    try:
        all_rooms = []
        total_areas = sum(len(areas) for areas in METROPOLITAN_AREAS.values())
        current_count = 0

        print(f"📍 수집 시작: {total_areas}개 기초자치단체")
        for region_name, areas in METROPOLITAN_AREAS.items():
            print(
                f"📋 {region_name}: {len(areas)}개 - {', '.join(areas[:5])}{'...' if len(areas) > 5 else ''}"
            )
        print("=" * 80)

        for region_name, areas in METROPOLITAN_AREAS.items():
            print(f"\n🌟 {region_name} 지역 시작 ({len(areas)}개 지역)")

            for i, area in enumerate(areas, 1):
                current_count += 1

                try:
                    area_rooms = crawler.process_area_with_subdivision(
                        area, region_name
                    )
                    all_rooms.extend(area_rooms)

                    # 진행률 표시
                    total_elapsed = time.time() - start_time
                    print_progress(
                        current_count,
                        total_areas,
                        area,
                        len(area_rooms),
                        total_elapsed,
                        region_name,
                    )

                    # 중간 저장 (10개 지역마다)
                    if current_count % 10 == 0:
                        print(f"\n    💾 중간 저장: {len(all_rooms):,}개 매물")
                        save_results_complete(all_rooms)

                    # 지역 간 딜레이
                    if current_count < total_areas:
                        print()  # 새 줄
                        region_type = (
                            "seoul"
                            if region_name == "서울특별시"
                            else (
                                "incheon" if region_name == "인천광역시" else "gyeonggi"
                            )
                        )
                        crawler.adaptive_delay(region_type)

                except KeyboardInterrupt:
                    print(f"\n⏹️ 사용자 중단 - {current_count}개 지역 완료")
                    break
                except Exception as e:
                    print(f"\n❌ {region_name} {area} 처리 실패: {str(e)[:50]}")
                    continue

            if current_count != sum(
                len(areas)
                for areas in list(METROPOLITAN_AREAS.values())[
                    : list(METROPOLITAN_AREAS.keys()).index(region_name) + 1
                ]
            ):
                break  # 사용자 중단 시 전체 중단

        # 최종 결과
        total_time = time.time() - start_time

        print(f"\n\n📊 수집 완료!")
        print(f"🏙️ 처리 완료: {current_count}개 기초자치단체")
        print(f"🏢 총 매물 수: {len(all_rooms):,}개")
        print(f"📋 발견된 필드 수: {len(crawler.all_fields_discovered)}개")
        print(f"⏰ 총 소요시간: {int(total_time//60):02d}:{int(total_time%60):02d}")

        # 실패한 지역 보고
        if crawler.failed_areas:
            print(f"\n⚠️ 실패한 지역 ({len(crawler.failed_areas)}개):")
            for failed_area in crawler.failed_areas:
                print(f"  - {failed_area}")

        # 지역별 통계
        region_stats = {}
        for room in all_rooms:
            region = room.get("region_name", "Unknown")
            region_stats[region] = region_stats.get(region, 0) + 1

        print(f"\n📈 지역별 매물 수:")
        for region, count in sorted(
            region_stats.items(), key=lambda x: x[1], reverse=True
        ):
            if region != "Unknown":
                print(f"  📍 {region}: {count:,}개")

        # 최종 저장
        save_results_complete(all_rooms)

        # 발견된 주요 필드 출력
        if crawler.all_fields_discovered:
            print(f"\n📋 발견된 주요 필드 (상위 20개):")
            sorted_fields = sorted(list(crawler.all_fields_discovered))
            for i, field in enumerate(sorted_fields[:20], 1):
                print(f"  {i:2d}. {field}")

            if len(sorted_fields) > 20:
                print(f"  ... 및 {len(sorted_fields) - 20}개 추가 필드")

    except KeyboardInterrupt:
        print("\n⏹️ 크롤링 중단")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n🔧 리소스 정리 중...")
        crawler.close()
        print("✅ 크롤링 완료!")


if __name__ == "__main__":
    main()
