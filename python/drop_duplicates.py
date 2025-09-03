import pandas as pd
from tqdm import tqdm

# tqdm pandas 연동 설정
tqdm.pandas()

# 파일 경로
input_file = "../next/kakaoMapViewer/public/reservation/reservation_4w_250903.csv"
output_file = "deduplicated_data.csv"

# CSV 불러오기
df = pd.read_csv(input_file)

# 중복 확인용 진행 표시
print("중복 여부 검사 중...")
duplicate_flags = df.duplicated(subset="rid", keep="first")
for i in tqdm(range(len(df)), desc="중복 확인 진행 중"):
    _ = duplicate_flags.iloc[i]  # 단순 진행률 표시 목적

# 중복 제거
deduplicated_df = df.drop_duplicates(subset="rid", keep="first")

# 저장
deduplicated_df.to_csv(output_file, index=False, encoding="utf-8-sig")

# 결과 요약 출력
print(f"\n✅ 중복 제거 완료: {len(df) - len(deduplicated_df)}개 중복 제거됨")
print(f"📁 저장 위치: {output_file}")
