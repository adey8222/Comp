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
    page_title="CIP • Internal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "employees" not in st.session_state:
    st.session_state.employees = None
if "import_errors" not in st.session_state:
    st.session_state.import_errors = []


def fmt_usd(n: float) -> str:
    return f"${n:,.0f}"


st.title("Compensation Intelligence Platform")
st.caption("CIP • Internal — Streamlit edition (upload workbook, view aggregates & export)")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Employees", "Departments", "Import"],
    label_visibility="collapsed",
)

df: pd.DataFrame | None = st.session_state.employees

if page == "Import":
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

elif page == "Dashboard":
    st.header("Dashboard")
    if df is None or df.empty:
        st.info("No data yet. Go to **Import** and upload your compensation workbook.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Employees", f"{len(df):,}")
        c2.metric("Departments", df["department"].nunique())
        c3.metric("Eligible", f"{df['eligibility'].sum():,}")
        c4.metric("Total salary (USD)", fmt_usd(df["usdCurrentSalary"].sum()))
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
        st.metric("Headcount", len(sub))
        st.metric("USD salary total", fmt_usd(sub["usdCurrentSalary"].sum()))
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
st.sidebar.markdown(
    "**GitHub files for Streamlit Cloud**\n"
    "- `streamlit_app.py` (this app)\n"
    "- `requirements.txt`\n"
    "- `cip_normalize.py`\n"
    "- `.streamlit/config.toml` (optional)\n"
    "- Secrets: `FX_RATES_STUB` in Cloud UI"
)
