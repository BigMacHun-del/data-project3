# [실습 3] Pandas EDA · Polars Lazy · DuckDB SQL 비교

**작성자**: 김대훈
**작성일**: 2026년 7월 16일
**대상 데이터**: `sales_100k.csv` (1,000,000행, 11개 컬럼)

같은 집계 작업(region·category별 총매출/평균/건수)을 **Pandas, Polars Lazy API, DuckDB SQL** 세 가지 방식으로 각각 구현하고, `timeit`으로 실행 성능까지 비교하는 실습입니다.

---

## 1. 데이터 개요

| 컬럼 | 설명 |
|---|---|
| order_id | 주문 ID |
| order_date | 주문일자 |
| region | 지역 (결측 10,000건) |
| category | 카테고리 (결측 8,000건) |
| product_name | 상품명 |
| quantity | 수량 |
| unit_price | 단가 |
| payment_method | 결제수단 |
| customer_age | 고객 나이 |
| customer_gender | 고객 성별 |
| amount | 거래 금액 (결측 5,000건) |

`region`, `category`, `amount` 세 컬럼에 결측치가 존재하며, 이 중 `amount`는 이상치 처리와 집계의 기준 컬럼이라 특히 주의가 필요합니다.

---

## 2. 실습 구성 (4단계)

### 1) Pandas EDA — 기초 탐색 + 이상치 처리
- `df.info()`, `df.isnull().sum()`으로 기초 탐색
- **IQR(사분위 범위) 방법**으로 `amount` 이상치 제거
  - `lower_bound = Q1 - 1.5*IQR`, `upper_bound = Q3 + 1.5*IQR`
  - `between()`으로 정상 범위 필터링 (NaN은 자동으로 False 처리되어 함께 제거됨)
- 이상치 제거 전·후 행 수 및 제거 비율 출력

### 2) Pandas groupby — named aggregation
- `region`·`category`별 **total(총매출)**, **mean(평균)**, **count(건수)** 계산
- `agg(total=('amount','sum'), mean=('amount','mean'), count=('amount','count'))` 형태의 **named aggregation**으로 결과 컬럼명 직접 지정
- 총매출(`total`) 내림차순 정렬

### 3) Polars Lazy API — 동일 집계
- `scan_csv → filter → group_by → agg → sort → collect` 체인으로 동일한 집계 수행
- `scan_csv`(즉시 로딩 X)로 시작해 **Lazy evaluation** 유지, 체인 끝에 `.collect()`로 실제 실행
- IQR 경계값(`lower_bound`, `upper_bound`)은 Pandas 파트에서 계산한 값을 그대로 재사용해 세 도구 간 비교 기준을 통일

### 4) DuckDB SQL + 성능 비교
- 동일 집계를 `SELECT ... GROUP BY ... ORDER BY` SQL로 작성, `.df()`로 결과를 pandas DataFrame으로 변환
- `timeit`으로 Pandas / Polars / DuckDB 세 도구의 실행 시간을 **동일 반복 횟수(20회)** 로 측정 및 비교

---

## 3. 예외처리

치명적 오류(파일 없음, 필수 컬럼 없음, 데이터 전부 결측 등)는 원인을 안내하는 메시지를 출력하고 `sys.exit(1)`로 즉시 종료합니다. timeit 성능 비교 구간은 세 도구를 개별적으로 격리해서, 한 도구가 실패해도 나머지 도구 비교는 계속 진행됩니다.

| 구간 | 예외 상황 | 처리 |
|---|---|---|
| CSV 로딩 | 파일 없음 / 빈 파일 / 기타 오류 | 메시지 출력 후 종료 |
| 컬럼 확인 | `region`/`category`/`amount` 누락 | 메시지 출력 후 종료 |
| IQR 계산 | `amount` 전체 결측 | `ValueError` 처리 후 종료 |
| 행 수 비율 계산 | 원본 데이터 0행 (0으로 나누기 방지) | 분기 처리 |
| 이상치 제거 후 데이터 0행 | 이후 집계 무의미 | 조기 종료 |
| Pandas groupby | 대상 컬럼 없음 | `KeyError` 처리 |
| Polars 집계 | 파싱/쿼리 오류 | `pl.exceptions.PolarsError` 처리 |
| DuckDB 쿼리 | SQL/파일 오류 | `duckdb.Error` 처리 |
| timeit 비교 | 개별 도구 실행 실패 | 해당 도구만 "측정 실패" 표시, 나머지는 계속 진행 |

---

## 4. 실행 방법

```bash
# 필요 패키지 설치
python3 -m pip install pandas polars duckdb

# project.py와 sales_100k.csv를 같은 폴더에 두고 실행
python3 project.py
```

## 5. 실행 결과 요약

### 지역별 집계 (상위 예시)
서울이 카테고리 불문 지역 중 총매출 1위(카테고리별 약 720~750억), 그 다음 경기, 부산 순으로 나타났습니다.

### 성능 비교 (timeit, 20회 반복, 1,000,000행 기준)

| 도구 | 총 시간 | 평균 1회 |
|---|---|---|
| Pandas | 37.02초 | 1.85초 |
| Polars | 6.92초 | 0.35초 |
| DuckDB | 10.75초 | 0.54초 |

Pandas 대비 **Polars 약 5.4배, DuckDB 약 3.4배 빠른 성능**을 보였습니다. Polars와 DuckDB는 lazy evaluation과 쿼리 최적화(predicate/projection pushdown, 벡터화 실행)를 활용하는 반면, Pandas는 매 실행마다 CSV 전체를 즉시 로딩하고 순차적으로 연산하기 때문에 차이가 발생합니다.

> 참고: Pandas의 기본 `groupby()`는 결측치(NaN) 그룹을 자동으로 제외하지만, Polars/DuckDB는 결측치도 하나의 그룹(`null`)으로 포함시킵니다. 세 도구의 결과 행 수가 다르게 보인다면 이 차이 때문입니다.

---

## 6. 버전 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| 0.1 | 2026-07-16 | 최초 작성 — Pandas EDA 기초 탐색 + 이상치 처리 |
| 0.2 | 2026-07-16 | Pandas groupby named aggregation 추가 |
| 0.3 | 2026-07-16 | Polars Lazy API 동일 집계 추가 |
| 0.4 | 2026-07-16 | DuckDB SQL 동일 집계 + 세 도구 성능 비교(timeit 5회) 추가 |
| 0.5 | 2026-07-16 | 주석 보강, timeit 반복 횟수 5회 → 20회 상향 |
| 0.6 | 2026-07-16 | 집계 컬럼명 avg/cnt → mean/count 통일, 출력 헤더 문구 통일 |
| 0.7 | 2026-07-16 | 파일 로딩/컬럼 존재/집계/timeit 구간 예외처리 추가 |