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
    # 문자열에 콤마가 있을 경우 제거 후 변환
    cleaned_str = str(val).replace(",", "").strip()
    try:
        return int(cleaned_str)
    except ValueError:
        return 0


# 데이터 추출
for age in age_categories:
    male_col = f"남_{age}"
    female_col = f"여_{age}"

    m_val = parse_int(selected_data.get(male_col, 0))
    f_val = parse_int(selected_data.get(female_col, 0))

    # 남성 인구수는 왼쪽 배치를 위해 음수로 변환
    male_counts.append(-abs(m_val))
    female_counts.append(abs(f_val))

# 4. Plotly 가로 막대 그래프 그리기
fig = go.Figure()

# 남성 막대 그래프 (왼쪽)
fig.add_trace(
    go.Bar(
        y=age_categories,
        x=male_counts,
        name="남성",
        orientation="h",
        marker=dict(color="#6BAED6"),
        hovertemplate="%{y} 남성: %{customdata:,}명<extra></extra>",
        customdata=[-val for val in male_counts],
    )
)

# 여성 막대 그래프 (오른쪽)
fig.add_trace(
    go.Bar(
        y=age_categories,
        x=female_counts,
        name="여성",
        orientation="h",
        marker=dict(color="#FC9272"),
        hovertemplate="%{y} 여성: %{x:,}명<extra></extra>",
    )
)

# 5. 레이아웃 및 세로축 고정 설정
max_male = max([-x for x in male_counts]) if male_counts else 0
max_female = max(female_counts) if female_counts else 0
max_pop = max(max_male, max_female)
axis_range = max_pop * 1.15 if max_pop > 0 else 100

fig.update_layout(
    title=dict(
        text=f"📊 {selected_sido} {selected_sigungu} {selected_dong} 인구 피라미드 ({latest_year}년)",
        font=dict(size=20),
    ),
    barmode="overlay",
    bargap=0.1,
    height=800,
    legend=dict(x=0.85, y=1.05, orientation="h"),
    xaxis=dict(
        title="인구수 (명)",
        range=[-axis_range, axis_range],
        tickvals=[
            -int(axis_range * 0.8),
            -int(axis_range * 0.4),
            0,
            int(axis_range * 0.4),
            int(axis_range * 0.8),
        ],
        ticktext=[
            f"{int(axis_range * 0.8):,}",
            f"{int(axis_range * 0.4):,}",
            "0",
            f"{int(axis_range * 0.4):,}",
            f"{int(axis_range * 0.8):,}",
        ],
    ),
    yaxis=dict(
        title="나이",
        type="category",
        categoryorder="array",
        categoryarray=age_categories,
    ),
    template="plotly_white",
)

# 6. 화면 출력
st.plotly_chart(fig, use_container_width=True)

st.info(
    "💡 Tip: 그래프 오른쪽 위의 도구 모음을 이용해 확대한 후 살펴보거나 이미지로 저장할 수 있습니다."
)
