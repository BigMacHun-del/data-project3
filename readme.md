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

---
---

# [실습 4] 시각화 4종 · 통계 검정 · sklearn Pipeline

**작성자**: 김대훈
**작성일**: 2026년 7월 16일
**대상 데이터**: `sales_100k.csv` (실습 3 연계)
**파일**: `practice4.py`

실습 3의 결과(IQR 이상치 제거된 데이터)를 이어받아 **EDA 시각화, 통계 검정(t-test/카이제곱), sklearn Pipeline, Plotly 인터랙티브 차트**로 확장하는 실습입니다.

---

## 1. 실습 3 → 4 연계 포인트

| 실습 3 산출물 | 실습 4 활용 |
|---|---|
| IQR 이상치 제거된 DataFrame | 시각화·통계 검정 입력 데이터로 사용 |
| region·category groupby 결과 | 카이제곱 분할표 기반 변수로 활용 |
| `sales_100k.csv` | Pipeline의 학습 데이터 원본 |

단, 실습 3 코드를 그대로 이어붙이는 게 아니라 `practice4.py`에서 **원본 CSV를 다시 읽고 동일한 IQR 로직을 재적용**해 `df_clean`을 만드는 방식입니다 (파일로 저장해서 넘기지 않음 — 이상치 제거는 실행 시점마다 메모리 안에서만 수행).

---

## 2. 실습 구성 (4단계)

### 1) EDA 시각화 4종 (2×2 서브플롯)
`fig, axes = plt.subplots(2, 2)`로 하나의 figure에 4개 차트 통합:
- **히스토그램 + KDE**: `amount` 분포 확인 (우측으로 긴 꼬리 형태)
- **박스플롯**: region별 `amount` 분포 비교
- **월별 라인 차트**: `order_date` 기반 월별 총매출 추세
- **상관 히트맵**: `quantity`, `unit_price`, `customer_age`, `amount` 간 상관관계

OS별로 설치된 한글 폰트가 달라 matplotlib 폰트를 **자동 탐지**하도록 구성 (`AppleGothic`→macOS, `Malgun Gothic`→Windows, `Noto Sans CJK`→Linux 순으로 탐색).

### 2) 통계 검정 — t-test + 카이제곱
- **t-test**: 서울 vs 부산 평균 매출(`amount`) 차이를 `scipy.stats.ttest_ind`(Welch's t-test)로 검정, t-통계량·p-value 출력 후 `p < 0.05` 기준 유의미 여부 해석 문구 출력
- **카이제곱 검정**: `category` × `payment_method` 분할표를 `pd.crosstab`으로 생성 후 `chi2_contingency`로 독립성 검정, p-value 해석 문구 출력

### 3) sklearn Pipeline 구성 + 저장
- `quantity`, `unit_price`, `customer_age`(수치형) + `region`, `category`, `payment_method`, `customer_gender`(범주형)로 `amount`를 예측하는 회귀 모델
- `ColumnTransformer`(수치형 StandardScaler / 범주형 SimpleImputer+OneHotEncoder) + `LinearRegression`을 하나의 `Pipeline` 객체로 구성
- `fit → predict → score` 순서 진행 후 `joblib.dump()`로 모델 저장, `joblib.load()`로 재로딩해 점수 일치 확인

### 4) Plotly 인터랙티브 차트
- 지역·카테고리별 총매출을 `plotly.express.bar`로 시각화 (`barmode="group"`)
- `fig.show()` 대신 `.write_html()`로 `sales_by_region_category.html` 파일 저장

---

## 3. 예외처리

실습 3과 동일한 원칙: **뒤 단계 전체가 무의미해지는 치명적 오류**는 즉시 종료하고, **한 파트 실패가 다른 파트에 영향 없는 경우**는 격리해서 나머지를 계속 진행합니다.

| 구간 | 예외 상황 | 처리 |
|---|---|---|
| CSV 로딩 | 파일 없음 / 빈 파일 / 기타 오류 | 메시지 출력 후 종료 |
| 컬럼 확인 | 필수 컬럼(9개) 누락 | 메시지 출력 후 종료 |
| IQR 계산 | `amount` 전체 결측 | `ValueError` 처리 후 종료 |
| 이상치 제거 후 데이터 0행 | 이후 분석 무의미 | 조기 종료 |
| `order_date` 변환 | 날짜 형식이 아닌 값 | `ValueError`/`TypeError` 처리 후 종료 |
| 1) 시각화 4종 | 차트 생성 중 오류 | 경고만 출력, 종료하지 않고 통계 검정 등 계속 진행 |
| 2-1) t-test | 서울/부산 데이터 없음 | 사전 분기 처리로 검정 생략 |
| 2-2) 카이제곱 | 분할표가 비어있거나 전부 0 | `ValueError` 처리 |
| 3) Pipeline 학습/예측 | 학습 실패 | `sys.exit(1)` (이후 저장이 무의미하므로) |
| 3) 모델 저장/재로딩 | 디스크 쓰기/읽기 실패 | `OSError`/`IOError` 개별 처리 |
| 4) Plotly HTML 저장 | 디스크 쓰기 실패 | `OSError`/`IOError` 처리 |

---

## 4. 실행 방법

```bash
# 필요 패키지 설치
python3 -m pip install matplotlib seaborn scipy scikit-learn joblib plotly

# practice4.py와 sales_100k.csv를 같은 폴더에 두고 실행
python3 practice4.py
```

실행하면 다음 3개 파일이 생성됩니다.
- `eda_4charts.png` — EDA 시각화 4종
- `sales_amount_pipeline.pkl` — 학습된 회귀 Pipeline 모델
- `sales_by_region_category.html` — Plotly 인터랙티브 막대 차트

---

## 5. 실행 결과 요약

### 시각화
- `amount` 분포는 우측으로 긴 꼬리 형태 (저가 거래가 압도적으로 많음)
- region별 `amount` 분포는 거의 동일한 모양 (지역 간 거래 단가 차이 크지 않음)
- 월별 매출은 뚜렷한 추세 없이 등락 반복
- `amount`는 `unit_price`(0.66), `quantity`(0.63)와 상관관계 있음, `customer_age`와는 무관(0.00)

### 통계 검정
| 검정 | 통계량 | p-value | 해석 |
|---|---|---|---|
| t-test (서울 vs 부산) | t = 0.7269 | 0.4673 | 유의미한 차이 없음 |
| 카이제곱 (category × payment_method) | χ² = 13.5300 | 0.8889 | 서로 독립 (연관성 없음) |

### Pipeline
- 테스트 데이터 R² = **0.8411** — `quantity`, `unit_price` 위주로 매출을 잘 설명 (구조상 `amount ≈ quantity × unit_price`라 자연스러운 결과)
- 저장 후 재로딩한 모델도 동일 R² 확인
- 참고: `LinearRegression` 특성상 예측값에 음수가 나올 수 있음 (실제 매출은 음수가 될 수 없는데도) — 선형회귀의 한계로, 필요시 로그 변환 타겟이나 후처리(`max(0, pred)`)로 보완 가능

### Plotly 차트
지역·카테고리별 총매출 인터랙티브 막대 차트 — 서울(70B대)이 압도적 1위, 경기(58~59B), 부산(35~36B) 순으로 실습 3 결과와 일관성 확인

---

## 6. 버전 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| 0.1 | 2026-07-16 | 최초 작성 — 데이터 로딩 + IQR 이상치 처리 (실습 3 연계) |
| 0.2 | 2026-07-16 | EDA 시각화 4종 (2×2 서브플롯) 추가 |
| 0.3 | 2026-07-16 | 한글 폰트 하드코딩 → OS별 자동 탐지 방식으로 수정 (macOS 한글 깨짐 해결) |
| 0.4 | 2026-07-16 | 통계 검정 추가 (서울 vs 부산 t-test, category × payment_method 카이제곱) |
| 0.5 | 2026-07-16 | sklearn Pipeline 구성 + 저장/재로딩 추가 (amount 예측 회귀 모델) |
| 0.6 | 2026-07-16 | Plotly 인터랙티브 막대 차트 추가, HTML 저장 |
| 0.7 | 2026-07-16 | 전 구간(로딩/시각화/통계검정/Pipeline/Plotly)에 예외처리 추가 |