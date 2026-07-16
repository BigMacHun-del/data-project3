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
# 0.4 : 2026년 7월 16일 - DuckDB SQL 동일 집계 + 세 도구 성능 비교(timeit, 반복 횟수 5회) 추가
#                       Pandas  : 총 2.6501초  (평균 0.5300초/회)
#                       Polars  : 총 0.1845초  (평균 0.0369초/회)
#                       DuckDB  : 총 0.5792초  (평균 0.1158초/회)
# 0.5 : 2026년 7월 16일 - 주석 보강, timeit 반복 횟수 5회 -> 20회로 상향
#.                      Pandas  : 총 10.4271초  (평균 0.5214초/회)
#                       Polars  : 총 0.7560초  (평균 0.0378초/회)
#                       DuckDB  : 총 2.3606초  (평균 0.1180초/회)
# 0.6 : 2026년 7월 16일 - 집계 컬럼명 avg/cnt -> mean/count로 통일, 출력 헤더 문구 통일
# 0.7 : 2026년 7월 16일 - 파일 로딩/컬럼 존재/집계/timeit 구간에 예외처리 추가
# --------------

import sys
import pandas as pd
import polars as pl
import duckdb
import timeit

FILE_PATH = "sales_100k.csv"
REQUIRED_COLUMNS = {"region", "category", "amount"}

# 1. 기초 탐색 및 이상치 처리
# 데이터 로딩
try:
    df = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"[오류] '{FILE_PATH}' 파일을 찾을 수 없습니다. 코드와 같은 폴더에 있는지 확인해주세요.")
    sys.exit(1)
except pd.errors.EmptyDataError:
    print(f"[오류] '{FILE_PATH}' 파일에 데이터가 없습니다.")
    sys.exit(1)
except Exception as e:
    print(f"[오류] CSV 로딩 중 예상치 못한 문제가 발생했습니다: {e}")
    sys.exit(1)

# 필수 컬럼 존재 확인 (없으면 이후 연산이 전부 의미 없으므로 여기서 종료)
missing_cols = REQUIRED_COLUMNS - set(df.columns)
if missing_cols:
    print(f"[오류] 필수 컬럼이 없습니다: {missing_cols}")
    sys.exit(1)

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
try:
    Q1 = df["amount"].quantile(0.25)  # 1사분위수
    Q3 = df["amount"].quantile(0.75)  # 3사분위수
    IQR = Q3 - Q1  # 사분위 범위

    if pd.isna(Q1) or pd.isna(Q3):
        # amount 컬럼이 전부 결측치인 극단적인 경우
        raise ValueError("amount 컬럼에 유효한 값이 없어 IQR을 계산할 수 없습니다.")

    lower_bound = Q1 - 1.5 * IQR  # 이상치 판단 하한선
    upper_bound = Q3 + 1.5 * IQR  # 이상치 판단 상한선
except ValueError as e:
    print(f"[오류] IQR 계산 실패: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("[3] IQR 이상치 처리 (amount 기준)")
print("=" * 50)
print(f"Q1 = {Q1:,.2f}")
print(f"Q3 = {Q3:,.2f}")
print(f"IQR = {IQR:,.2f}")
print(f"정상 범위 = [{lower_bound:,.2f}, {upper_bound:,.2f}]")

df_clean = df[df["amount"].between(lower_bound, upper_bound)]  # 정상 범위 내 행만 필터링

# 제거 전 / 후 행 수 출력
print("\n" + "=" * 50)
print("[4] 이상치 제거 전 / 후 행 수 비교")
print("=" * 50)
if len(df) == 0:
    print("[오류] 원본 데이터가 비어있어 비율을 계산할 수 없습니다.")
else:
    print(f"제거 전 행 수 : {len(df):,}")
    print(f"제거 후 행 수 : {len(df_clean):,}")
    print(f"제거된 행 수  : {len(df) - len(df_clean):,}")
    print(f"제거 비율     : {(len(df) - len(df_clean)) / len(df) * 100:.2f}%")

if len(df_clean) == 0:
    # 이후 groupby, 성능 비교 모두 무의미하므로 여기서 종료
    print("[오류] 이상치 제거 후 남은 데이터가 없어 이후 집계를 진행할 수 없습니다.")
    sys.exit(1)

# 2. Pandas groupby named aggregation
try:
    result = (
        df_clean.groupby(["region", "category"])  # region, category 조합별로 그룹화
        .agg(
            total=("amount", "sum"),   # named aggregation: 컬럼명을 total로 직접 지정
            mean=("amount", "mean"),
            count=("amount", "count"),
        )
        .reset_index()  # groupby 결과를 다시 일반 컬럼 형태로 변환
    )
    result = result.sort_values("total", ascending=False).reset_index(drop=True)
except KeyError as e:
    print(f"[오류] Pandas 집계 실패 - 컬럼을 찾을 수 없습니다: {e}")
    sys.exit(1)

# 출력 (가독성을 위해 천단위 콤마 포맷)
result_display = result.copy()
result_display["total"] = result_display["total"].map(lambda x: f"{x:,.0f}")
result_display["mean"] = result_display["mean"].map(lambda x: f"{x:,.0f}")

print("\n" + "=" * 50)
print("[5] Pandas groupby region·category별 집계 (총매출 내림차순)")
print("=" * 50)
print(result_display.to_string(index=False))


# 3. Polars Lazy API로 동일 집계 작성
try:
    result_pl = (
        pl.scan_csv(FILE_PATH)  # Lazy로 CSV를 스캔 (즉시 로딩 X)
        .filter(
            pl.col("amount").is_between(lower_bound, upper_bound)  # Pandas와 동일한 IQR 경계 재사용
        )
        .group_by(["region", "category"])
        .agg(
            pl.col("amount").sum().alias("total"),
            pl.col("amount").mean().alias("mean"),
            pl.col("amount").count().alias("count"),
        )
        .sort("total", descending=True)
        .collect()  # 여기서 실제 쿼리 실행 및 최적화 적용
    )
except pl.exceptions.PolarsError as e:
    print(f"[오류] Polars 집계 실패: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("[6] Polars Lazy API region·category별 집계 (총매출 내림차순)")
print("=" * 50)
result_pl_display = result_pl.with_columns(
    pl.col("total").round(0),
    pl.col("mean").round(0),
)
with pl.Config(tbl_rows=-1, thousands_separator=True, fmt_float="full"):  # 지수표기 방지 + 천단위 구분
    print(result_pl_display)

# 4-1. DuckDB SQL로 동일 집계 작성
duckdb_query = f"""
SELECT
    region,
    category,
    SUM(amount) AS total,
    AVG(amount) AS mean,
    COUNT(*)    AS count
FROM read_csv_auto('{FILE_PATH}')
WHERE amount BETWEEN {lower_bound} AND {upper_bound}
GROUP BY region, category
ORDER BY total DESC
"""

try:
    result_duckdb = duckdb.sql(duckdb_query).df()  # 쿼리 결과를 pandas DataFrame으로 변환
except duckdb.Error as e:
    print(f"[오류] DuckDB 쿼리 실행 실패: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("[7] DuckDB SQL region·category별 집계 (총매출 내림차순)")
print("=" * 50)
result_duckdb_display = result_duckdb.copy()
result_duckdb_display["total"] = result_duckdb_display["total"].map(lambda x: f"{x:,.0f}")
result_duckdb_display["mean"] = result_duckdb_display["mean"].map(lambda x: f"{x:,.0f}")
print(result_duckdb_display.to_string(index=False))


# 4-2. 세 도구 성능 비교 (timeit, 동일 반복 횟수)
def run_pandas():
    # 매 반복마다 로딩부터 집계까지 전 과정을 새로 수행 (공정 비교를 위해 캐시 없이 처음부터)
    df_ = pd.read_csv(FILE_PATH)
    q1_ = df_["amount"].quantile(0.25)
    q3_ = df_["amount"].quantile(0.75)
    iqr_ = q3_ - q1_
    lb_ = q1_ - 1.5 * iqr_
    ub_ = q3_ + 1.5 * iqr_
    clean_ = df_[df_["amount"].between(lb_, ub_)]
    return (
        clean_.groupby(["region", "category"])
        .agg(total=("amount", "sum"), mean=("amount", "mean"), count=("amount", "count"))
        .sort_values("total", ascending=False)
    )


def run_polars():
    return (
        pl.scan_csv(FILE_PATH)
        .filter(pl.col("amount").is_between(lower_bound, upper_bound))
        .group_by(["region", "category"])
        .agg(
            pl.col("amount").sum().alias("total"),
            pl.col("amount").mean().alias("mean"),
            pl.col("amount").count().alias("count"),
        )
        .sort("total", descending=True)
        .collect()
    )


def run_duckdb():
    return duckdb.sql(duckdb_query).df()


NUMBER = 20  # 세 도구 동일 반복 횟수 (5 -> 20으로 상향, 측정 신뢰도 개선)

# 세 도구 각각 실행 실패 시 해당 도구만 건너뛰고 나머지 비교는 계속 진행
timings = {}
for tool_name, func in (("Pandas", run_pandas), ("Polars", run_polars), ("DuckDB", run_duckdb)):
    try:
        timings[tool_name] = timeit.timeit(func, number=NUMBER)
    except Exception as e:
        print(f"[오류] {tool_name} 성능 측정 실패: {e}")
        timings[tool_name] = None

print("\n" + "=" * 50)
print(f"[8] 성능 비교 (timeit, 반복 횟수={NUMBER}회 동일)")
print("=" * 50)
for tool_name, elapsed in timings.items():
    if elapsed is None:
        print(f"{tool_name:<7} : 측정 실패 (위 오류 메시지 참고)")
    else:
        print(f"{tool_name:<7} : 총 {elapsed:.4f}초  (평균 {elapsed / NUMBER:.4f}초/회)")