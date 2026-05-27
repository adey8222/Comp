"""
Compensation Intelligence Platform — Streamlit edition for Community Cloud.

Deploy on https://share.streamlit.io with main file: streamlit_app.py
Dependencies: requirements.txt at repo root.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from cip_normalize import load_and_normalize

st.set_page_config(
    page_title="Compensation Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DARK_THEME_CSS = """
<style>
.stApp {
    background: #050b12;
    color: #f8fafc;
}

section[data-testid="stSidebar"] {
    background: #0b1220;
    border-right: 1px solid #1f2a3a;
}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #f8fafc !important;
    font-weight: 600;
}

p, label, .stCaption {
    color: #94a3b8;
}

.hero {
    padding: 2rem 2.25rem;
    margin-bottom: 1.5rem;
    border: 1px solid #1f2a3a;
    border-radius: 24px;
    background: linear-gradient(135deg, #07111f, #0b1020);
    box-shadow: 0 0 30px rgba(0, 255, 255, 0.08);
}

.hero h1 {
    margin: 0.35rem 0 0.5rem 0 !important;
    background: linear-gradient(90deg, #a5f3fc, #f8fafc, #ddd6fe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.metric-card {
    padding: 1.5rem;
    border: 1px solid #1f2a3a;
    border-radius: 20px;
    background: #07111f;
    min-height: 6rem;
}

.small-label {
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 0.75rem;
    margin-bottom: 0.5rem;
}

.big-number {
    color: #f8fafc;
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.2;
}

.panel {
    padding: 1.25rem 1.5rem;
    border: 1px solid #1f2a3a;
    border-radius: 20px;
    background: #07111f;
    margin-bottom: 1rem;
}

div[data-testid="stMetric"] {
    background: #07111f;
    border: 1px solid #1f2a3a;
    border-radius: 16px;
    padding: 1rem 1.25rem;
}

div[data-testid="stMetric"] label {
    color: #94a3b8 !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #f8fafc !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #1f2a3a;
    border-radius: 16px;
    overflow: hidden;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0891b2, #6366f1);
    border: 1px solid rgba(34, 211, 238, 0.35);
    color: #f8fafc;
}

.stButton > button[kind="primary"]:hover {
    border-color: #22d3ee;
    box-shadow: 0 0 20px rgba(34, 211, 238, 0.25);
}

div[data-testid="stFileUploader"] {
    border: 1px dashed #334155;
    border-radius: 16px;
    padding: 0.5rem;
    background: #07111f;
}

div[data-baseweb="notification"] {
    border-radius: 12px;
}
</style>
"""

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

if "employees" not in st.session_state:
    st.session_state.employees = None
if "import_errors" not in st.session_state:
    st.session_state.import_errors = []


def fmt_usd(n: float) -> str:
    return f"${n:,.0f}"


def metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="small-label">{label}</div>
            <div class="big-number">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="hero">
        <div class="small-label">CIP • Internal</div>
        <h1>Compensation Intelligence Platform</h1>
        <p style="margin:0; color:#94a3b8; font-size:0.95rem;">
            Imports, normalization, FX → USD, and recommendation ranges — Streamlit edition
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Employees", "Departments", "Import"],
    label_visibility="collapsed",
)

df: pd.DataFrame | None = st.session_state.employees

if page == "Import":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.header("Import")
    st.markdown(
        "Upload **CSV**, **XLS**, or **XLSX**. Headers are auto-mapped "
        "(e.g. `Departments` → department, `Email` → company email). "
        "Data is kept in this session (Streamlit Cloud resets when the app sleeps)."
    )
    up = st.file_uploader("Spreadsheet", type=["csv", "xls", "xlsx"])
    if up is not None:
        if st.button("Load & normalize", type="primary"):
            with st.spinner("Parsing…"):
                loaded, errs = load_and_normalize(up)
            st.session_state.employees = loaded if len(loaded) else None
            st.session_state.import_errors = errs
            if len(loaded):
                st.success(f"Loaded {len(loaded):,} employees.")
            else:
                st.error("No valid rows imported.")
            if errs:
                st.warning(f"{len(errs)} row(s) skipped.")
                with st.expander("Row errors"):
                    st.code("\n".join(errs[:50]) + ("\n…" if len(errs) > 50 else ""))
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Dashboard":
    st.header("Dashboard")
    if df is None or df.empty:
        st.info("No data yet. Go to **Import** and upload your compensation workbook.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Employees", f"{len(df):,}")
        with c2:
            metric_card("Departments", str(df["department"].nunique()))
        with c3:
            metric_card("Eligible", f"{int(df['eligibility'].sum()):,}")
        with c4:
            metric_card("Total salary (USD)", fmt_usd(df["usdCurrentSalary"].sum()))
        st.subheader("By department")
        by_dept = (
            df.groupby("department", as_index=False)
            .agg(
                headcount=("fullName", "count"),
                usd_salary=("usdCurrentSalary", "sum"),
            )
            .sort_values("usd_salary", ascending=False)
        )
        by_dept["usd_salary"] = by_dept["usd_salary"].map(fmt_usd)
        st.dataframe(by_dept, use_container_width=True, hide_index=True)
        st.subheader("Currency mix")
        mix = (
            df.groupby("currentSalaryCurrency", as_index=False)
            .agg(count=("fullName", "count"), usd_total=("usdCurrentSalary", "sum"))
            .sort_values("usd_total", ascending=False)
        )
        st.dataframe(mix, use_container_width=True, hide_index=True)

elif page == "Employees":
    st.header("Employees")
    if df is None or df.empty:
        st.info("Import data first.")
    else:
        q = st.text_input("Search name, email, or department")
        view = df
        if q.strip():
            mask = (
                view["fullName"].str.contains(q, case=False, na=False)
                | view["companyEmail"].str.contains(q, case=False, na=False)
                | view["department"].str.contains(q, case=False, na=False)
            )
            view = view[mask]
        show = [
            "fullName",
            "companyEmail",
            "department",
            "jobTitle",
            "currentSalaryCurrency",
            "currentSalary",
            "usdCurrentSalary",
            "eligibility",
            "recRaisePctMin",
            "recRaisePctMax",
        ]
        st.dataframe(view[show], use_container_width=True, hide_index=True)
        buf = io.BytesIO()
        view.to_csv(buf, index=False)
        st.download_button(
            "Download CSV",
            buf.getvalue(),
            file_name="cip_employees.csv",
            mime="text/csv",
        )

elif page == "Departments":
    st.header("Departments")
    if df is None or df.empty:
        st.info("Import data first.")
    else:
        dept = st.selectbox("Department", sorted(df["department"].unique()))
        sub = df[df["department"] == dept]
        c1, c2 = st.columns(2)
        with c1:
            metric_card("Headcount", str(len(sub)))
        with c2:
            metric_card("USD salary total", fmt_usd(sub["usdCurrentSalary"].sum()))
        st.dataframe(
            sub[
                [
                    "fullName",
                    "jobTitle",
                    "officeLocation",
                    "currentSalary",
                    "currentSalaryCurrency",
                    "usdCurrentSalary",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

st.sidebar.divider()
st.sidebar.caption(
    "Deploy: `streamlit_app.py` + `requirements.txt` + `cip_normalize.py`. "
    "Load data via **Import**."
)
