# --------------
# 작성자 : 김대훈
# 작성목적 : Pandas EDA · Polars Lazy · DuckDB SQL 비교 실습 (Practice 3)
# 작성일 : 2026년 7월 16일
# 
# Pandas EDA, Polars Lazy, DuckDB SQL 비교 실습하는 프로젝트입니다.
#
# 변경사항 내역
# 0.1 : 2026년 7월 16일 - 최초 작성 Pandas EDA 기초 탐색 + 이상치 처리
# --------------

import pandas as pd

# 데이터 로딩
df = pd.read_csv("sales_100k.csv")

# 기초 탐색 (df.info(), isnull().sum())
print("=" * 50)
print("[1] df.info()")
print("=" * 50)
df.info()

print("\n" + "=" * 50)
print("[2] 결측치 확인 (isnull().sum())")
print("=" * 50)
print(df.isnull().sum())

# IQR 방법으로 이상치 제거 (amount 기준)
# amount 자체에 결측치가 있으므로, IQR 계산 전 결측 행은 별도 확인만 하고
# between() 비교에서는 NaN이 자동으로 False 처리되어 함께 걸러짐
Q1 = df["amount"].quantile(0.25)
Q3 = df["amount"].quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

print("\n" + "=" * 50)
print("[3] IQR 이상치 처리 (amount 기준)")
print("=" * 50)
print(f"Q1 = {Q1:,.2f}")
print(f"Q3 = {Q3:,.2f}")
print(f"IQR = {IQR:,.2f}")
print(f"정상 범위 = [{lower_bound:,.2f}, {upper_bound:,.2f}]")

df_clean = df[df["amount"].between(lower_bound, upper_bound)]

# 3. 제거 전 / 후 행 수 출력
print("\n" + "=" * 50)
print("[4] 이상치 제거 전 / 후 행 수 비교")
print("=" * 50)
print(f"제거 전 행 수 : {len(df):,}")
print(f"제거 후 행 수 : {len(df_clean):,}")
print(f"제거된 행 수  : {len(df) - len(df_clean):,}")
print(f"제거 비율     : {(len(df) - len(df_clean)) / len(df) * 100:.2f}%")