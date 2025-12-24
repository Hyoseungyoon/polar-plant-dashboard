import streamlit as st
import pandas as pd
from pathlib import Path
import unicodedata
import io

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="EC값에 따른 상하부 길이의 성장률 차이",
    layout="wide"
)

# 한글 폰트 (Streamlit UI)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# Plotly 폰트용 공통 설정
PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

DATA_DIR = Path("data")

# -----------------------------
# 유틸 함수: 한글 파일 탐색
# -----------------------------
def find_file_by_name(directory: Path, target_name: str):
    if not directory.exists():
        return None

    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for f in directory.iterdir():
        name_nfc = unicodedata.normalize("NFC", f.name)
        name_nfd = unicodedata.normalize("NFD", f.name)
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return f
    return None

# -----------------------------
# 데이터 로딩
# -----------------------------
@st.cache_data
def load_env_data():
    school_files = {
        "송도고": "송도고_환경데이터.csv",
        "하늘고": "하늘고_환경데이터.csv",
        "아라고": "아라고_환경데이터.csv",
        "동산고": "동산고_환경데이터.csv",
    }

    data = {}
    for school, fname in school_files.items():
        file_path = find_file_by_name(DATA_DIR, fname)
        if file_path is None:
            st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {fname}")
            continue

        df = pd.read_csv(file_path)
        df["학교"] = school
        data[school] = df

    return data

@st.cache_data
def load_growth_data():
    file_path = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if file_path is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    xls = pd.ExcelFile(file_path)
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["학교"] = sheet
        data[sheet] = df
    return data

# -----------------------------
# 데이터 로딩
# -----------------------------
if not DATA_DIR.exists():
    st.error("❌ data/ 폴더를 찾을 수 없습니다. GitHub에 업로드되어 있는지 확인하세요.")
    st.stop()

with st.spinner("데이터 로딩 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# -----------------------------
# 사이드바
# -----------------------------
schools = ["전체"] + sorted(env_data.keys())
selected_school = st.sidebar.selectbox("학교 선택", schools)

st.title("📊 EC값에 따른 상하부 길이의 성장률 차이")

# -----------------------------
# 탭 구성
# -----------------------------
tab1, tab2, tab3 = st.tabs([
    "📘 학교별 평균 환경데이터 & 이탈값",
    "📈 EC값에 따른 성장량 (학교별)",
    "🔗 EC–지상부/지하부 관계"
])

# ======================================================
# TAB 1
# ======================================================
with tab1:
    rows = []
    outliers = []

    for school, df in env_data.items():
        rows.append({
            "학교": school,
            "평균 온도": df["temperature"].mean(),
            "평균 습도": df["humidity"].mean(),
            "평균 pH": df["ph"].mean(),
            "평균 EC": df["ec"].mean()
        })

        # 물리적으로 말이 안 되는 값 체크
        invalid = df[
            (df["ph"] < 0) | (df["ph"] > 14) |
            (df["humidity"] < 0) | (df["humidity"] > 100) |
            (df["ec"] < 0)
        ]
        if not invalid.empty:
            invalid = invalid.copy()
            invalid["학교"] = school
            outliers.append(invalid)

    avg_df = pd.DataFrame(rows)

    st.subheader("학교별 평균 환경 데이터")
    st.dataframe(avg_df, use_container_width=True)

    buffer = io.BytesIO()
    avg_df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button(
        "📥 평균 환경 데이터 다운로드",
        buffer,
        file_name="학교별_평균_환경데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if outliers:
        st.subheader("⚠️ 환경 데이터 이탈값")
        out_df = pd.concat(outliers)
        st.dataframe(out_df, use_container_width=True)

# ======================================================
# TAB 2
# ======================================================
with tab2:
    st.subheader("학교별 EC 조건에서의 성장량")

    ec_map = {
        "송도고": 1.0,
        "하늘고": 2.0,
        "아라고": 4.0,
        "동산고": 8.0
    }

    summary = []
    for school, df in growth_data.items():
        summary.append({
            "학교": school,
            "EC": ec_map.get(school, None),
            "평균 지상부 길이(mm)": df["지상부 길이(mm)"].mean(),
            "평균 지하부 길이(mm)": df["지하부길이(mm)"].mean()
        })

    sum_df = pd.DataFrame(summary)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["지상부 길이", "지하부 길이"]
    )

    fig.add_trace(
        go.Bar(
            x=sum_df["학교"],
            y=sum_df["평균 지상부 길이(mm)"],
            name="지상부"
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Bar(
            x=sum_df["학교"],
            y=sum_df["평균 지하부 길이(mm)"],
            name="지하부"
        ),
        row=1, col=2
    )

    fig.update_layout(
        height=400,
        font=PLOTLY_FONT
    )

    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# TAB 3
# ======================================================
with tab3:
    st.subheader("EC값에 따른 지상부–지하부 관계")

    all_rows = []
    for school, df in growth_data.items():
        ec = ec_map.get(school, None)
        temp = df.copy()
        temp["EC"] = ec
        all_rows.append(temp)

    merged = pd.concat(all_rows, ignore_index=True)

    fig1 = px.scatter(
        merged,
        x="지상부 길이(mm)",
        y="지하부길이(mm)",
        color="EC",
        hover_data=["학교"],
        title="지상부 길이 vs 지하부 길이"
    )
    fig1.update_layout(font=PLOTLY_FONT)

    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("""
    **해석 포인트**
    - EC가 증가함에 따라 지상부와 지하부의 성장 비율이 달라지는 경향을 확인할 수 있다.
    - 고 EC 구간에서는 지하부 비중이 상대적으로 커지는 패턴이 나타난다.
    """)

