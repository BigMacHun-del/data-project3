# --------------
# 작성자 : 김대훈
# 작성목적 : 시각화 4종 · 통계 검정 · sklearn Pipeline 실습 (Practice 4)
# 작성일 : 2026년 7월 16일
#
# 실습 3(sales_100k.csv IQR 이상치 처리) 결과를 이어받아
# EDA 시각화, t-test/카이제곱 검정, sklearn Pipeline, Plotly 차트를 진행합니다.
#
# 변경사항 내역
# 0.1 : 2026년 7월 16일 - 최초 작성 (데이터 로딩 + IQR 이상치 처리, 실습 3 연계)
# 0.2 : 2026년 7월 16일 - EDA 시각화 4종 (2x2 서브플롯: 히스토그램+KDE / 박스플롯 / 월별 라인 / 상관 히트맵) 추가
# 0.3 : 2026년 7월 16일 - 한글 폰트 하드코딩(Noto Sans CJK JP) -> OS별 자동 탐지 방식으로 수정
#                       (macOS에서 한글이 네모(tofu)로 깨지는 문제 해결)
# 0.4 : 2026년 7월 16일 - 통계 검정 추가 (서울 vs 부산 t-test, category x payment_method 카이제곱)
# --------------

import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from scipy import stats

FILE_PATH = "sales_100k.csv"

# 한글 폰트 설정 - OS별로 설치된 한글 폰트가 다르므로, 시스템에 설치된 폰트 중
# 사용 가능한 것을 자동으로 찾아 적용 (없으면 경고만 출력하고 기본 폰트로 진행)
import matplotlib.font_manager as fm

_KOREAN_FONT_CANDIDATES = [
    "AppleGothic",          # macOS 기본 탑재
    "Apple SD Gothic Neo",  # macOS
    "Malgun Gothic",        # Windows 기본 탑재
    "NanumGothic",          # Linux (nanum 폰트 설치 시)
    "Noto Sans CJK KR",     # Linux (Noto CJK 개별 파일 설치 시)
    "Noto Sans CJK JP",     # Linux (Noto CJK 통합 파일, 한글 글리프 포함)
]
_installed_fonts = {f.name for f in fm.fontManager.ttflist}
_selected_font = next((f for f in _KOREAN_FONT_CANDIDATES if f in _installed_fonts), None)

if _selected_font:
    mpl.rcParams["font.family"] = _selected_font
else:
    print("[경고] 시스템에서 한글 폰트를 찾지 못했습니다. 차트의 한글이 깨질 수 있습니다.")

mpl.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

# -----------------------------
# 0. 데이터 로딩 + IQR 이상치 제거 (실습 3과 동일한 전처리 로직 재사용)
# -----------------------------
try:
    df = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"[오류] '{FILE_PATH}' 파일을 찾을 수 없습니다. 코드와 같은 폴더에 있는지 확인해주세요.")
    sys.exit(1)

Q1 = df["amount"].quantile(0.25)
Q3 = df["amount"].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

df_clean = df[df["amount"].between(lower_bound, upper_bound)].copy()

# order_date를 datetime으로 변환 (월별 라인 차트에 사용)
df_clean["order_date"] = pd.to_datetime(df_clean["order_date"])
df_clean["order_month"] = df_clean["order_date"].dt.to_period("M").astype(str)

print(f"[데이터 준비 완료] 이상치 제거 후 {len(df_clean):,}행")

# -----------------------------
# 1. EDA 시각화 4종 (2x2 서브플롯 - 하나의 figure에 통합)
# -----------------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("EDA 시각화 4종 - amount 기준", fontsize=16)

# (1) 히스토그램 + KDE - amount 분포 확인
sns.histplot(df_clean["amount"], kde=True, ax=axes[0, 0], color="steelblue")
axes[0, 0].set_title("1) 히스토그램 + KDE (amount 분포)")
axes[0, 0].set_xlabel("amount")

# (2) 박스플롯 - region별 amount 분포 비교
sns.boxplot(data=df_clean, x="region", y="amount", ax=axes[0, 1])
axes[0, 1].set_title("2) 박스플롯 (region별 amount 분포)")
axes[0, 1].tick_params(axis="x", rotation=45)

# (3) 월별 라인 차트 - 월별 총매출 추세
monthly_total = df_clean.groupby("order_month")["amount"].sum().sort_index()
axes[1, 0].plot(monthly_total.index, monthly_total.values, marker="o", color="darkorange")
axes[1, 0].set_title("3) 월별 라인 차트 (월별 총매출 추세)")
axes[1, 0].tick_params(axis="x", rotation=45)
axes[1, 0].set_ylabel("총매출")

# (4) 상관 히트맵 - 수치형 변수 간 상관관계
numeric_cols = ["quantity", "unit_price", "customer_age", "amount"]
corr = df_clean[numeric_cols].corr()
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=axes[1, 1])
axes[1, 1].set_title("4) 상관 히트맵 (수치형 변수)")

plt.tight_layout()
plt.savefig("eda_4charts.png", dpi=150)
print("[저장 완료] eda_4charts.png")
plt.show()


# -----------------------------
# 2-1. t-test - 서울 vs 부산 평균 매출(amount) 차이 검정
# -----------------------------
seoul_amount = df_clean[df_clean["region"] == "서울"]["amount"]
busan_amount = df_clean[df_clean["region"] == "부산"]["amount"]

t_stat, t_pvalue = stats.ttest_ind(seoul_amount, busan_amount, equal_var=False)  # Welch's t-test (분산 동일 가정 X)

print("\n" + "=" * 50)
print("[t-test] 서울 vs 부산 평균 매출(amount) 차이")
print("=" * 50)
print(f"서울 평균 : {seoul_amount.mean():,.0f}  (n={len(seoul_amount):,})")
print(f"부산 평균 : {busan_amount.mean():,.0f}  (n={len(busan_amount):,})")
print(f"t-statistic = {t_stat:.4f}, p-value = {t_pvalue:.4f}")

# p-value 해석 (유의수준 0.05 기준)
if t_pvalue < 0.05:
    print("=> p < 0.05 이므로 서울과 부산의 평균 매출 차이는 통계적으로 유의미합니다.")
else:
    print("=> p >= 0.05 이므로 서울과 부산의 평균 매출 차이는 통계적으로 유의미하지 않습니다.")


# -----------------------------
# 2-2. 카이제곱 검정 - category x payment_method 독립성 검정
# -----------------------------
contingency_table = pd.crosstab(df_clean["category"], df_clean["payment_method"])

chi2_stat, chi2_pvalue, dof, expected = stats.chi2_contingency(contingency_table)

print("\n" + "=" * 50)
print("[카이제곱 검정] category x payment_method 독립성 검정")
print("=" * 50)
print("분할표 (contingency table):")
print(contingency_table)
print(f"\nchi2-statistic = {chi2_stat:.4f}, p-value = {chi2_pvalue:.4f}, 자유도(dof) = {dof}")

# p-value 해석 (유의수준 0.05 기준)
if chi2_pvalue < 0.05:
    print("=> p < 0.05 이므로 category와 payment_method는 서로 독립이 아닙니다 (연관성이 있습니다).")
else:
    print("=> p >= 0.05 이므로 category와 payment_method는 서로 독립입니다 (연관성이 없습니다).")