import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit + Plotly)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

DATA_DIR = Path("data")

SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#1f77b4"},
    "하늘고": {"ec": 2.0, "color": "#2ca02c"},  # 최적
    "아라고": {"ec": 4.0, "color": "#ff7f0e"},
    "동산고": {"ec": 8.0, "color": "#d62728"},
}

# ===============================
# 유틸: NFC/NFD 안전 파일 찾기
# ===============================
def normalize(s, form):
    return unicodedata.normalize(form, s)

def find_file_by_name(directory: Path, target_name: str):
    target_nfc = normalize(target_name, "NFC")
    target_nfd = normalize(target_name, "NFD")
    for f in directory.iterdir():
        if normalize(f.name, "NFC") == target_nfc or normalize(f.name, "NFD") == target_nfd:
            return f
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_env_data():
    env_data = {}
    for school in SCHOOL_INFO.keys():
        fname = f"{school}_환경데이터.csv"
        file_path = find_file_by_name(DATA_DIR, fname)
        if file_path is None:
            st.error(f"환경 데이터 파일을 찾을 수 없습니다: {fname}")
            return None
        df = pd.read_csv(file_path)
        df["학교"] = school
        env_data[school] = df
    return env_data

@st.cache_data
def load_growth_data():
    fname = "4개교_생육결과데이터.xlsx"
    file_path = find_file_by_name(DATA_DIR, fname)
    if file_path is None:
        st.error("생육 결과 데이터 파일을 찾을 수 없습니다.")
        return None

    xls = pd.ExcelFile(file_path)
    growth_data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        growth_data[sheet] = df
    return growth_data

with st.spinner("데이터 불러오는 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_INFO.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tabs = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# TAB 1 : 실험 개요
# ===============================
with tabs[0]:
    st.subheader("연구 배경 및 목적")
    st.write(
        "본 연구는 극지식물의 생육에 영향을 미치는 EC 농도의 최적 조건을 규명하기 위해 "
        "4개 고등학교에서 공동으로 실험을 수행하고 그 결과를 비교·분석한 것이다."
    )

    info_rows = []
    total_plants = 0
    for school, info in SCHOOL_INFO.items():
        n = len(growth_data.get(school, []))
        total_plants += n
        info_rows.append([school, info["ec"], n, info["color"]])

    info_df = pd.DataFrame(
        info_rows,
        columns=["학교", "EC 목표", "개체수", "시각화 색상"]
    )
    st.dataframe(info_df, use_container_width=True)

    all_env = pd.concat(env_data.values())
    avg_temp = all_env["temperature"].mean()
    avg_hum = all_env["humidity"].mean()

    avg_weights = {
        SCHOOL_INFO[k]["ec"]: v["생중량(g)"].mean()
        for k, v in growth_data.items()
    }
    optimal_ec = max(avg_weights, key=avg_weights.get)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_plants)
    c2.metric("평균 온도 (°C)", f"{avg_temp:.2f}")
    c3.metric("평균 습도 (%)", f"{avg_hum:.2f}")
    c4.metric("최적 EC", optimal_ec)

# ===============================
# TAB 2 : 환경 데이터
# ===============================
with tabs[1]:
    st.subheader("학교별 환경 평균 비교")

    summary = []
    for school, df in env_data.items():
        summary.append([
            school,
            df["temperature"].mean(),
            df["humidity"].mean(),
            df["ph"].mean(),
            df["ec"].mean(),
            SCHOOL_INFO[school]["ec"]
        ])

    sum_df = pd.DataFrame(
        summary,
        columns=["학교", "온도", "습도", "pH", "실측 EC", "목표 EC"]
    )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "EC 비교"]
    )

    fig.add_bar(x=sum_df["학교"], y=sum_df["온도"], row=1, col=1)
    fig.add_bar(x=sum_df["학교"], y=sum_df["습도"], row=1, col=2)
    fig.add_bar(x=sum_df["학교"], y=sum_df["pH"], row=2, col=1)

    fig.add_bar(x=sum_df["학교"], y=sum_df["실측 EC"], name="실측", row=2, col=2)
    fig.add_bar(x=sum_df["학교"], y=sum_df["목표 EC"], name="목표", row=2, col=2)

    fig.update_layout(height=600, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("선택한 학교 시계열")

    schools_to_plot = (
        SCHOOL_INFO.keys() if school_option == "전체" else [school_option]
    )

    for school in schools_to_plot:
        df = env_data[school]
        fig_line = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            subplot_titles=["온도", "습도", "EC"]
        )
        fig_line.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1)
        fig_line.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1)
        fig_line.add_scatter(x=df["time"], y=df["ec"], row=3, col=1)
        fig_line.add_hline(
            y=SCHOOL_INFO[school]["ec"],
            line_dash="dash",
            row=3, col=1
        )
        fig_line.update_layout(
            title=school,
            height=500,
            font=PLOTLY_FONT
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with st.expander("환경 데이터 원본"):
        env_all = pd.concat(env_data.values())
        st.dataframe(env_all)
        buf = io.BytesIO()
        env_all.to_csv(buf, index=False)
        buf.seek(0)
        st.download_button(
            "CSV 다운로드",
            data=buf,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ===============================
# TAB 3 : 생육 결과
# ===============================
with tabs[2]:
    st.subheader("EC별 평균 생중량")

    rows = []
    for school, df in growth_data.items():
        rows.append([
            SCHOOL_INFO[school]["ec"],
            df["생중량(g)"].mean(),
            school
        ])
    weight_df = pd.DataFrame(rows, columns=["EC", "평균 생중량", "학교"])

    best_ec = weight_df.loc[weight_df["평균 생중량"].idxmax()]["EC"]
    st.metric("🥇 최고 평균 생중량 EC", best_ec)

    fig_bar = px.bar(
        weight_df,
        x="EC",
        y="평균 생중량",
        color="학교",
        text_auto=".2f"
    )
    fig_bar.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("학교별 생중량 분포")
    dist_df = pd.concat(growth_data.values())
    fig_box = px.box(
        dist_df,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("상관관계 분석")
    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.scatter(
            dist_df,
            x="잎 수(장)",
            y="생중량(g)",
            color="학교",
            trendline="ols"
        )
        fig1.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = px.scatter(
            dist_df,
            x="지상부 길이(mm)",
            y="생중량(g)",
            color="학교",
            trendline="ols"
        )
        fig2.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(dist_df)
        buf = io.BytesIO()
        dist_df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buf,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
