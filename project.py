# --------------
# 작성자 : 김대훈
# 작성목적 : Pandas EDA · Polars Lazy · DuckDB SQL 비교 실습 (Practice 3)
# 작성일 : 2026년 7월 16일
# 
# Pandas EDA, Polars Lazy, DuckDB SQL 비교 실습하는 프로젝트입니다.
#
# 변경사항 내역
# 0.1 : 2026년 7월 16일 - 최초 작성 Pandas EDA 기초 탐색 + 이상치 처리
# 0.2 : 2026년 7월 16일 - Pandas groupby named aggregation 추가
# 0.3 : 2026년 7월 16일 - Polars Lazy API 동일 집계 추가
# --------------

import pandas as pd
import polars as pl

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

# 제거 전 / 후 행 수 출력
print("\n" + "=" * 50)
print("[4] 이상치 제거 전 / 후 행 수 비교")
print("=" * 50)
print(f"제거 전 행 수 : {len(df):,}")
print(f"제거 후 행 수 : {len(df_clean):,}")
print(f"제거된 행 수  : {len(df) - len(df_clean):,}")
print(f"제거 비율     : {(len(df) - len(df_clean)) / len(df) * 100:.2f}%")

# 2. Pandas groupby named aggregation
result = (
    df_clean.groupby(["region", "category"])
    .agg(
        total=("amount", "sum"),
        avg=("amount", "mean"),
        cnt=("amount", "count"),
    )
    .reset_index()
)

# 총매출 내림차순 정렬
result = result.sort_values("total", ascending=False).reset_index(drop=True)

# 출력 (가독성을 위해 천단위 콤마 포맷)
result_display = result.copy()
result_display["total"] = result_display["total"].map(lambda x: f"{x:,.0f}")
result_display["avg"] = result_display["avg"].map(lambda x: f"{x:,.0f}")

print("\n" + "=" * 50)
print("[5] Pandas region·category별 집계 (총매출 내림차순)")
print("=" * 50)
print(result_display.to_string(index=False))


# 3. Polars Lazy API로 동일 집계 작성
result_pl = (
    pl.scan_csv("sales_100k.csv")
    .filter(
        pl.col("amount").is_between(lower_bound, upper_bound)
    )
    .group_by(["region", "category"])
    .agg(
        pl.col("amount").sum().alias("total"),
        pl.col("amount").mean().alias("avg"),
        pl.col("amount").count().alias("cnt"),
    )
    .sort("total", descending=True)
    .collect()
)

print("\n" + "=" * 50)
print("[6] Polars Lazy API region·category별 집계 (총매출 내림차순)")
print("=" * 50)
result_pl_display = result_pl.with_columns(
    pl.col("total").round(0),
    pl.col("avg").round(0),
)
with pl.Config(tbl_rows=-1, thousands_separator=True, fmt_float="full"):
    print(result_pl_display)