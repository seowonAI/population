import json
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="전국 고령화 단계구분도", layout="wide")

st.title("🗺️ 2026년 전국 시군구별 고령화율 단계구분도")
st.caption(
    "주민등록 인구통계 데이터를 바탕으로 시군구별 65세 이상 고령인구 비율(%)을 시각화합니다."
)


# 1. 데이터 로드 (캐싱 적용)
@st.cache_data
def load_data():
    csv_url = "https://raw.githubusercontent.com/seowonAI/population/main/population_ts_yearly_gender.zip"
    geojson_url = "https://raw.githubusercontent.com/seowonAI/population/main/sigungu_kr.geojson.txt"

    # 1-1. GeoJSON 로드
    res = requests.get(geojson_url)
    res.raise_for_status()
    geojson_data = res.json()

    # 1-2. CSV 로드
    df = pd.read_csv(csv_url, encoding="utf-8")

    # 코드 전처리 (5자리 문자열)
    df["코드"] = df["코드"].astype(str).str.zfill(5)
    df["연도"] = df["연도"].astype(str)

    # 2026년 데이터 필터링
    df_2026 = df[df["연도"].str.contains("2026")].copy()
    df_2026["sigungu_code"] = df_2026["코드"].str[:5]

    # '계_' 시작 컬럼 필터링 (계_총인구수 제외)
    total_pop_cols = [
        col
        for col in df_2026.columns
        if col.startswith("계_") and col not in ["계_총인구수"]
    ]

    # 65세 이상 컬럼
    elderly_cols = []
    for col in total_pop_cols:
        age_str = col.replace("계_", "").replace("세", "").replace(" 이상", "")
        if age_str.isdigit() and int(age_str) >= 65:
            elderly_cols.append(col)
        elif "100" in age_str:
            elderly_cols.append(col)

    # 쉼표(,) 제거 및 정수 변환
    for col in total_pop_cols:
        if df_2026[col].dtype == object:
            df_2026[col] = (
                df_2026[col].astype(str).str.replace(",", "").astype(float)
            )

    # 1-3. 시군구별 인구 합산
    df_2026["전체인구"] = df_2026[total_pop_cols].sum(axis=1)
    df_2026["고령인구"] = df_2026[elderly_cols].sum(axis=1)

    grouped = (
        df_2026.groupby("sigungu_code")
        .agg(
            {
                "시도": "first",
                "시군구": "first",
                "전체인구": "sum",
                "고령인구": "sum",
            }
        )
        .reset_index()
    )

    # 고령화율(%) 계산
    grouped["고령화율"] = np.where(
        grouped["전체인구"] > 0,
        (grouped["고령인구"] / grouped["전체인구"]) * 100,
        0,
    )
    grouped["고령화율"] = grouped["고령화율"].round(2)

    return geojson_data, grouped


with st.spinner("데이터를 로드하고 고령화율을 계산 중입니다..."):
    geojson_data, df_sigungu = load_data()

# 2. Plotly 단계구분도 생성 (mapbox 기반)
fig = px.choropleth_mapbox(
    df_sigungu,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="고령화율",
    color_continuous_scale="Reds",
    range_color=(df_sigungu["고령화율"].min(), df_sigungu["고령화율"].max()),
    mapbox_style="carto-positron",  # 지도 배경 타일 표시
    center={"lat": 35.9, "lon": 127.8},
    zoom=6.2,
    hover_name="시군구",
    hover_data={"sigungu_code": False, "시도": True, "고령화율": ":.2f%"},
    labels={"고령화율": "고령화율(%)", "시도": "시도명"},
)

# 레이아웃 수정 (오류 발생 원인 속성 제거 및 안전한 구조 적용)
fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=750,
    coloraxis_colorbar=dict(
        title="고령화율(%)",
        ticksuffix="%",
    ),
)

# 3. Streamlit 화면 출력
st.plotly_chart(fig, use_container_width=True)

# 요약 카드
col1, col2, col3 = st.columns(3)
with col1:
    max_row = df_sigungu.loc[df_sigungu["고령화율"].idxmax()]
    st.metric(
        "고령화율 최고 지역",
        f"{max_row['시도']} {max_row['시군구']}",
        f"{max_row['고령화율']}%",
    )
with col2:
    min_row = df_sigungu.loc[df_sigungu["고령화율"].idxmin()]
    st.metric(
        "고령화율 최저 지역",
        f"{min_row['시도']} {min_row['시군구']}",
        f"{min_row['고령화율']}%",
    )
with col3:
    avg_rate = round(
        (df_sigungu["고령인구"].sum() / df_sigungu["전체인구"].sum()) * 100, 2
    )
    st.metric("전국 평균 고령화율", f"{avg_rate}%")
