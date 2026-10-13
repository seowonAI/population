import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 페이지 기본 설정 (타이틀 및 레이아웃)
st.set_page_config(page_title="동네별 인구 피라미드", layout="wide")


# 1. 데이터 불러오기 함수 (캐싱을 적용하여 앱 속도 최적화)
@st.cache_data
def load_data():
    # github/blob 주소 대신 raw 파일 다운로드 주소 사용
    url = "https://raw.githubusercontent.com/seowonAI/population/main/population_ts_yearly_gender.zip"

    # zip 압축 파일 형태의 CSV를 판다스로 직접 읽어옵니다.
    df = pd.read_csv(url)

    # 가장 최근 연도(최댓값) 데이터만 추출합니다.
    latest_year = df["연도"].max()
    df_latest = df[df["연도"] == latest_year].copy()

    return df_latest, latest_year


# 데이터 로드
try:
    df, latest_year = load_data()
except Exception as e:
    st.error(
        f"데이터를 불러오는 중 오류가 발생했습니다. 주소나 파일 형태를 확인해 주세요: {e}"
    )
    st.stop()

# 애플리케이션 제목 및 안내 메시지
st.title("🏡 우리 동네 인구 피라미드")
st.caption(
    f"가장 최근 데이터인 **{latest_year}년** 전국 읍·면·동 인구 데이터를 기반으로 시각화합니다."
)
st.write("---")

# 2. 지역 선택 드롭다운 3단계 (시도 -> 시군구 -> 동)
col1, col2, col3 = st.columns(3)

with col1:
    # 시도 목록 추출 후 선택
    sido_list = sorted(df["시도"].dropna().unique())
    selected_sido = st.selectbox("1. 시·도 선택", sido_list)

# 선택된 시도에 해당하는 데이터 필터링
df_sido = df[df["시도"] == selected_sido]

with col2:
    # 선택된 시도 내의 시군구 목록 추출 후 선택
    sigungu_list = sorted(df_sido["시군구"].dropna().unique())
    selected_sigungu = st.selectbox("2. 시·군·구 선택", sigungu_list)

# 선택된 시군구에 해당하는 데이터 필터링
df_sigungu = df_sido[df_sido["시군구"] == selected_sigungu]

with col3:
    # 선택된 시군구 내의 동 목록 추출 후 선택
    dong_list = sorted(df_sigungu["동"].dropna().unique())
    selected_dong = st.selectbox("3. 읍·면·동 선택", dong_list)

# 최종적으로 선택한 동네 1개 행 추출
target_row = df_sigungu[df_sigungu["동"] == selected_dong]

if target_row.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()

selected_data = target_row.iloc[0]

# 3. 나이별 남/여 인구 데이터 정리
# 0세부터 99세까지, 그리고 100세 이상 라벨 생성
age_categories = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_counts = []
female_counts = []

for age in age_categories:
    male_col = f"남_{age}"
    female_col = f"여_{age}"

    # 해당 열의 값을 가져오고, 결측치는 0으로 처리합니다.
    m_val = selected_data[male_col] if male_col in selected_data else 0
    f_val = selected_data[female_col] if female_col in selected_data else 0

    # 남성 인구수는 왼쪽 배치를 위해 음수로 변환합니다.
    male_counts.append(-abs(int(m_val)))
    female_counts.append(int(f_val))

# 4. Plotly 가로 막대 그래프 그리기
fig = go.Figure()

# 남성 막대 그래프 (왼쪽, 음수 값)
fig.add_trace(
    go.Bar(
        y=age_categories,  # 세로축: 나이
        x=male_counts,  # 가로축: 음수 처리된 남성 인구
        name="남성",
        orientation="h",
        marker=dict(color="#6BAED6"),  # 부드러운 따뜻한 파란톤
        # 마우스 호버 시 보여줄 텍스트 (양수 형태로 표시)
        hovertemplate="%{y} 남성: %{customdata:,}명<extra></extra>",
        customdata=[-val for val in male_counts],
    )
)

# 여성 막대 그래프 (오른쪽, 양수 값)
fig.add_trace(
    go.Bar(
        y=age_categories,  # 세로축: 나이
        x=female_counts,  # 가로축: 양수 여성 인구
        name="여성",
        orientation="h",
        marker=dict(color="#FC9272"),  # 따뜻한 붉은톤
        hovertemplate="%{y} 여성: %{x:,}명<extra></extra>",
    )
)

# 5. 그래프 레이아웃 및 세로축 순서 고정 설정
# 가로축 축 범위 계산 (최대 인구수에 맞추어 좌우 대칭)
max_pop = max(max([-x for x in male_counts]), max(female_counts))
axis_range = max_pop * 1.15 if max_pop > 0 else 100

fig.update_layout(
    title=dict(
        text=f"📊 {selected_sido} {selected_sigungu} {selected_dong} 인구 피라미드 ({latest_year}년)",
        font=dict(size=20),
    ),
    barmode="overlay",  # 두 막대를 중심 기준으로 포개어 표시
    bargap=0.1,  # 막대 간격
    height=800,  # 그래프 높이 (100개 이상의 나이 눈금이 잘 보이도록 설정)
    legend=dict(x=0.85, y=1.05, orientation="h"),
    xaxis=dict(
        title="인구수 (명)",
        range=[-axis_range, axis_range],  # 좌우 대칭 범위를 설정
        # 음수 표기를 양수로 변환하여 축에 표시
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
    yaxis
