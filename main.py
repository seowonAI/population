import json
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="전국 연령대별 단계구분도", layout="wide")

st.title("🗺️ 전국 시군구별 인구 구조 단계구분도")
st.caption(
    "주민등록 인구통계 데이터를 바탕으로 시군구별 고령인구 및 유소년인구 비율(%)을 시각화합니다."
)


# 1. GeoJSON 및 CSV 기초 데이터 로드 (캐싱)
@st.cache_data
def load_base_data():
    csv_url = "https://raw.githubusercontent.com/seowonAI/population/main/population_ts_yearly_gender.zip"
    geojson_url = "https://raw.githubusercontent.com/seowonAI/population/main/sigungu_kr.geojson.txt"

    # GeoJSON 다운로드
    res = requests.get(geojson_url)
    res.raise_for_status()
    geojson_data = res.json()

    # CSV 데이터 다운로드
    df = pd.read_csv(csv_url, encoding="utf-8")

    # 코드 및 연도 전처리
    df["코드"] = df["코드"].astype(str).str.zfill(5)
    df["연도"] = df["연도"].astype(str).str.extract(r"(\d{4})")[0]

    # 시군구 코드 5자리 추출 (Pandas Series 유지)
    sigungu_code = df["코드"].str[:5]

    # 행정구역 개편 예외 처리
    # 1) 군위군 보정 (47720 -> 27720)
    sigungu_code = sigungu_code.replace({"47720": "27720"})

    # 2) 강원특별자치도(42 -> 51), 전북특별자치도(45 -> 52) 앞 2자리 변경
    sigungu_code = sigungu_code.str.replace(
        r"^42", "51", regex=True
    ).str.replace(r"^45", "52", regex=True)

    df["sigungu_code"] = sigungu_code

    return geojson_data, df


with st.spinner("기초 데이터를 로드 중입니다..."):
    geojson_data, df_raw = load_base_data()

# 2. 사이드바 컨트롤러 (연도 선택, 지표 선택, 시도 선택)
available_years = sorted(df_raw["연도"].dropna().unique().tolist())
min_year, max_year = int(available_years[0]), int(available_years[-1])

with st.sidebar:
    st.header("⚙️ 지도 설정")

    selected_year = str(
        st.slider(
            "📅 연도 선택",
            min_value=min_year,
            max_value=max_year,
            value=max_year,
            step=1,
        )
    )

    indicator_type = st.radio(
        "📊 지표 선택",
        options=["고령화율 (65세 이상)", "유소년 비율 (0~14세)"],
        index=0,
    )

    # GeoJSON 내부 시도 목록 추출 (선택 드롭다운용)
    sido_options = ["전국"] + sorted(
        list(
            set(
                f["properties"]["시도"]
                for f in geojson_data["features"]
                if "시도" in f["properties"]
            )
        )
    )
    selected_sido = st.selectbox("📍 시도 선택 (확대 보기)", sido_options)


# 3. 데이터 집계 함수
def process_year_data(df, target_year, indicator):
    df_year = df[df["연도"] == target_year].copy()

    # 인구 관련 열 필터링 ('계_'로 시작하는 열)
    total_pop_cols = [
        col
        for col in df_year.columns
        if col.startswith("계_") and col not in ["계_총인구수"]
    ]

    # 숫자에 쉼표(,)가 있을 경우 처리
    for col in total_pop_cols:
        if df_year[col].dtype == object:
            df_year[col] = (
                df_year[col].astype(str).str.replace(",", "").astype(float)
            )

    # 연령대별 열 구분
    target_cols = []
    for col in total_pop_cols:
        age_str = col.replace("계_", "").replace("세", "").replace(" 이상", "")

        if indicator.startswith("고령화율"):
            # 65세 이상
            if (age_str.isdigit() and int(age_str) >= 65) or "100" in age_str:
                target_cols.append(col)
        else:
            # 0~14세 (유소년)
            if age_str.isdigit() and 0 <= int(age_str) <= 14:
                target_cols.append(col)

    df_year["전체인구"] = df_year[total_pop_cols].sum(axis=1)
    df_year["대상인구"] = df_year[target_cols].sum(axis=1)

    grouped = (
        df_year.groupby("sigungu_code")
        .agg(
            {
                "시도": "first",
                "시군구": "first",
                "전체인구": "sum",
                "대상인구": "sum",
            }
        )
        .reset_index()
    )

    grouped["비율"] = np.where(
        grouped["전체인구"] > 0,
        (grouped["대상인구"] / grouped["전체인구"]) * 100,
        0,
    )
    grouped["비율"] = grouped["비율"].round(2)

    return grouped


df_sigungu = process_year_data(df_raw, selected_year, indicator_type)

# GeoJSON의 전체 시군구 코드 집합
geojson_codes = set(f["properties"]["코드"] for f in geojson_data["features"])
df_codes = set(df_sigungu["sigungu_code"].unique())
missing_codes = geojson_codes - df_codes


# 4. 상단 지표 카드 3장
col1, col2, col3 = st.columns(3)

total_target_pop = df_sigungu["대상인구"].sum()
total_all_pop = df_sigungu["전체인구"].sum()
nat_rate = (
    round((total_target_pop / total_all_pop) * 100, 2)
    if total_all_pop > 0
    else 0
)

indicator_label = "고령화율" if "고령화율" in indicator_type else "유소년 비율"

with col1:
    st.metric(f"전국 평균 {indicator_label}", f"{nat_rate}%")

with col2:
    if not df_sigungu.empty:
        max_row = df_sigungu.loc[df_sigungu["비율"].idxmax()]
        st.metric(
            f"가장 높은 시군구 ({max_row['시군구']})",
            f"{max_row['시도']} {max_row['시군구']}",
            f"{max_row['비율']}%",
        )

with col3:
    if not df_sigungu.empty:
        min_row = df_sigungu.loc[df_sigungu["비율"].idxmin()]
        st.metric(
            f"가장 낮은 시군구 ({min_row['시군구']})",
            f"{min_row['시도']} {min_row['시군구']}",
            f"{min_row['비율']}%",
        )


# 5. 지도 영역 및 줌/중심점 설정
center = {"lat": 35.9, "lon": 127.8}
zoom = 6.2

if selected_sido != "전국":
    sido_coords = []
    for f in geojson_data["features"]:
        if f["properties"].get("시도") == selected_sido:
            geom = f["geometry"]
            coords = geom["coordinates"]
            if geom["type"] == "Polygon":
                for poly in coords:
                    sido_coords.extend(poly)
            elif geom["type"] == "MultiPolygon":
                for multipoly in coords:
                    for poly in multipoly:
                        sido_coords.extend(poly)

    if sido_coords:
        lons = [c[0] for c in sido_coords]
        lats = [c[1] for c in sido_coords]
        center = {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons)}
        zoom = 8.2


# 6. 지표별 범주 색상 구간(Color Range) 설정
if "고령화율" in indicator_type:
    color_range = (19, 38)
    color_scale = "Reds"
else:
    color_range = (5, 20)
    color_scale = "Blues"


# 7. Plotly 단계구분도 생성 (px.choropleth_map)
fig = px.choropleth_map(
    df_sigungu,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="비율",
    color_continuous_scale=color_scale,
    range_color=color_range,
    map_style="carto-positron",
    center=center,
    zoom=zoom,
    hover_name="시군구",
    hover_data={"sigungu_code": False, "시도": True, "비율": ":.2f%"},
    labels={"비율": f"{indicator_label}(%)", "시도": "시도명"},
)

fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=720,
    coloraxis_colorbar=dict(
        title=f"{indicator_label}(%)",
        ticksuffix="%",
    ),
)

st.plotly_chart(fig, use_container_width=True)

# 8. 미매칭 행정구역 안내 문구
if missing_codes:
    missing_names = []
    for f in geojson_data["features"]:
        if f["properties"]["코드"] in missing_codes:
