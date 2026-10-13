import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="동네별 인구 피라미드", layout="wide")


# 1. 데이터 불러오기 함수
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/seowonAI/population/main/population_ts_yearly_gender.zip"

    # zip 압축 CSV 읽기
    df = pd.read_csv(url)

    # 가장 최근 연도 데이터만 추출
    latest_year = df["연도"].max()
    df_latest = df[df["연도"] == latest_year].copy()

    return df_latest, latest_year


# 데이터 로드
try:
    df, latest_year = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 애플리케이션 제목
st.title("🏡 우리 동네 인구 피라미드")
st.caption(
    f"가장 최근 데이터인 **{latest_year}년** 전국 읍·면·동 인구 데이터를 기반으로 시각화합니다."
)
st.write("---")

# 2. 지역 선택 드롭다운 3단계
col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df["시도"].dropna().unique())
    selected_sido = st.selectbox("1. 시·도 선택", sido_list)

df_sido = df[df["시도"] == selected_sido]

with col2:
    sigungu_list = sorted(df_sido["시군구"].dropna().unique())
    selected_sigungu = st.selectbox("2. 시·군·구 선택", sigungu_list)

df_sigungu = df_sido[df_sido["시군구"] == selected_sigungu]

with col3:
    dong_list = sorted(df_sigungu["동"].dropna().unique())
    selected_dong = st.selectbox("3. 읍·면·동 선택", dong_list)

# 선택한 동네 데이터
target_row = df_sigungu[df_sigungu["동"] == selected_dong]

if target_row.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()

selected_data = target_row.iloc[0]

# 3. 나이 카테고리 정의 (0세 ~ 100세 이상)
age_categories = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_counts = []
female_counts = []


# 안전하게 문자열/숫자를 정수로 변환하는 함수 (콤마 제거 등)
def parse_int(val):
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    cleaned_str = str(val).replace(",", "").strip()
    try:
        return int(cleaned_str)
    except ValueError:
        return 0


# 데이터 추출 및 리스트 구성
for age in age_categories:
    male_col = f"남_{age}"
    female_col = f"여_{age}"

    m_val = parse_int(selected_data.get(male_col, 0))
    f_val = parse_int(selected_data.get(female_col, 0))

    # 남성 인구수는 그래프 배치를 위해 음수로 변환
    male_counts.append(-abs(m_val))
    female_counts.append(abs(f_val))

# --- [추가기능 1] 통계 지표 계산 (총인구, 평균연령, 고령화율) ---
total_pop = 0  # 총 인구수
total_age_sum = 0  # (나이 * 인구수) 합계 (평균 연령 계산용)
elderly_pop = 0  # 65세 이상 인구수
youth_pop = 0  # 0~14세 유소년 인구수

for idx, age_label in enumerate(age_categories):
    m_pop = -male_counts[idx]
    f_pop = female_counts[idx]
    age_pop = m_pop + f_pop

    total_pop += age_pop

    # 100세 이상은 100세로 계산에 포함
    age_value = 100 if idx == 100 else idx
    total_age_sum += age_value * age_pop

    # 65세 이상 인구
    if idx >= 65:
        elderly_pop += age_pop

    # 0~14세 유소년 인구
    if idx <= 14:
        youth_pop += age_pop

# 평균연령 및 고령화율 계산
avg_age = (total_age_sum / total_pop) if total_pop > 0 else 0
elderly_ratio = (elderly_pop / total_pop * 100) if total_pop > 0 else 0

# --- [추가기능 2] 상단 지표 카드 3개 배치 ---
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.metric(label="👥 총인구", value=f"{total_pop:,} 명")

with m_col2:
    st.metric(label="🎂 평균
