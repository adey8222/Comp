"""
Compensation Intelligence Platform — Streamlit edition.

Bundled data loads automatically on first visit (data/compensation_employee_dataset_updated.xlsx).
Deploy: streamlit_app.py + requirements.txt + cip_normalize.py + cip_dashboard.py + data/*.xlsx
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from cip_dashboard import (
    BUNDLED_DATA_PATH,
    compute_dashboard_stats,
    fmt_usd,
    load_bundled_dataset,
    render_currency_table,
    render_department_table,
)
from cip_normalize import load_and_normalize

st.set_page_config(
    page_title="Compensation Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_THEME_CSS = """
<style>
.stApp { background: #0b0f14; color: #f8fafc; }
section[data-testid="stSidebar"] {
    background: #0b1220; border-right: 1px solid #1f2a3a;
}
section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}
h1, h2, h3 { color: #f8fafc !important; }
.hero {
    padding: 2rem 2.25rem; margin-bottom: 1.25rem;
    border: 1px solid rgba(255,255,255,0.08); border-radius: 24px;
    background: linear-gradient(135deg, rgba(6,16,28,0.95), rgba(11,16,32,0.9));
    box-shadow: 0 0 40px rgba(34, 211, 238, 0.06);
}
.hero h1 {
    margin: 0.35rem 0 0.5rem 0 !important;
    background: linear-gradient(90deg, #a5f3fc, #f8fafc, #ddd6fe);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-card {
    padding: 1.25rem 1.5rem; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px; background: rgba(15,23,42,0.65); min-height: 5.5rem;
}
.small-label {
    color: #71717a; text-transform: uppercase; letter-spacing: 0.2em;
    font-size: 0.65rem; margin-bottom: 0.35rem;
}
.metric-hint { color: #52525b; font-size: 0.6rem; margin-bottom: 0.25rem; }
.big-number { color: #fafafa; font-size: 1.75rem; font-weight: 700; }
.glass-section {
    border: 1px solid rgba(255,255,255,0.08); border-radius: 20px;
    background: rgba(15,23,42,0.5); margin-bottom: 1.25rem; overflow: hidden;
}
.glass-section-head {
    padding: 1rem 1.25rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    background: linear-gradient(90deg, rgba(34,211,238,0.08), transparent, rgba(167,139,250,0.08));
}
.glass-section-head h3 { margin: 0; font-size: 1.1rem; }
.glass-section-head p { margin: 0.25rem 0 0; color: #71717a; font-size: 0.75rem; }
.glass-section-body { padding: 0.5rem 0.25rem 1rem; }
.cip-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.cip-table th {
    text-align: left; padding: 0.75rem 1.25rem;
    color: #71717a; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
    background: rgba(255,255,255,0.04);
}
.cip-table td { padding: 0.75rem 1.25rem; color: #d4d4d8; border-top: 1px solid rgba(255,255,255,0.05); }
.cip-table td.num { font-variant-numeric: tabular-nums; }
.cip-table td.dept { color: #f4f4f5; font-weight: 500; }
.cur-pill {
    color: #a5f3fc; border-bottom: 1px dotted rgba(34,211,238,0.5); cursor: help;
}
.muted { color: #71717a; padding: 1rem 1.25rem; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0891b2, #6366f1);
    border: 1px solid rgba(34, 211, 238, 0.35); color: #f8fafc;
}
div[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; }
</style>
"""

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


def init_session() -> None:
    defaults = {
        "employees": None,
        "import_errors": [],
        "data_source": None,
        "selected_employee_idx": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


@st.cache_data(show_spinner="Loading compensation dataset…")
def cached_bundled_employees() -> pd.DataFrame:
    df, _errs = load_bundled_dataset()
    return df


def ensure_data_loaded() -> None:
    """Auto-load bundled xlsx whenever session has no roster (new visit / sleep wake)."""
    cur = st.session_state.employees
    if cur is not None and not cur.empty:
        return
    df = cached_bundled_employees()
    if df is not None and not df.empty:
        st.session_state.employees = df
        st.session_state.data_source = "bundled"
        st.session_state.import_errors = []


def metric_card(title: str, value: str, hint: str = "") -> None:
    hint_html = f'<div class="metric-hint">{hint}</div>' if hint else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="small-label">{title}</div>
            {hint_html}
            <div class="big-number">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def glass_section(title: str, subtitle: str, body_html: str) -> None:
    st.markdown(
        f"""
        <div class="glass-section">
            <div class="glass-section-head">
                <h3>{title}</h3>
                <p>{subtitle}</p>
            </div>
            <div class="glass-section-body">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


init_session()
ensure_data_loaded()

st.markdown(
    """
    <div class="hero">
        <div class="small-label">CIP • Internal</div>
        <h1>Compensation Intelligence Platform</h1>
        <p style="margin:0; color:#94a3b8; font-size:0.9rem;">
            Imports, normalization, FX → USD, and configurable recommendation ranges
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
source = st.session_state.data_source or "none"

st.sidebar.caption(
    f"**Data:** {len(df):,} employees" if df is not None and not df.empty else "**Data:** none"
)
if source == "bundled":
    st.sidebar.caption("Source: bundled dataset (auto-loaded)")
elif source == "upload":
    st.sidebar.caption("Source: your upload (this session)")

if page == "Dashboard":
    st.header("Dashboard")
    if df is None or df.empty:
        st.warning(
            f"No employee data loaded. Bundled file expected at `{BUNDLED_DATA_PATH.name}` in the "
            "`data/` folder — push it to GitHub or use **Import**."
        )
    else:
        stats = compute_dashboard_stats(df)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            metric_card("Total employees", f"{stats.total_employees:,}", "active cycle")
        with c2:
            metric_card("Eligible", f"{stats.eligible_count:,}", "flagged in source")
        with c3:
            metric_card("Payroll (USD)", fmt_usd(stats.total_payroll_usd), "normalized")
        with c4:
            metric_card(
                "Bonus + raises (USD)",
                fmt_usd(stats.total_bonus_usd + stats.total_raise_usd),
                "normalized",
            )
        with c5:
            metric_card("Departments", str(len(stats.departments)), "unique")

        glass_section(
            "Currency mix",
            "Headcount and local salary rollups — hover currency for USD conversion",
            render_currency_table(stats.currencies),
        )
        glass_section(
            "Department mesh",
            "Payroll, bonus, and merit pools in USD",
            render_department_table(stats.departments),
        )

elif page == "Import":
    st.header("Import")
    st.markdown(
        "Replace the in-memory roster with a new upload, or reset to the **bundled** dataset shipped in this repo."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Reset to bundled dataset", type="secondary"):
            st.session_state.employees = cached_bundled_employees()
            st.session_state.data_source = "bundled"
            st.session_state.import_errors = []
            st.rerun()
    with col_b:
        if st.button("Clear data", type="secondary"):
            st.session_state.employees = None
            st.session_state.data_source = None
            st.rerun()

    up = st.file_uploader("Spreadsheet", type=["csv", "xls", "xlsx"])
    if up is not None and st.button("Load & normalize", type="primary"):
        with st.spinner("Parsing…"):
            loaded, errs = load_and_normalize(up)
        st.session_state.employees = loaded if len(loaded) else None
        st.session_state.import_errors = errs
        st.session_state.data_source = "upload" if len(loaded) else None
        if len(loaded):
            st.success(f"Loaded {len(loaded):,} employees.")
            st.rerun()
        else:
            st.error("No valid rows imported.")
        if errs:
            st.warning(f"{len(errs)} row(s) skipped.")
            with st.expander("Row errors"):
                st.code("\n".join(errs[:50]) + ("\n…" if len(errs) > 50 else ""))

elif page == "Employees":
    st.header("Employees")
    if df is None or df.empty:
        st.info("No roster loaded.")
    else:
        q = st.text_input("Search name, email, or department")
        view = df.copy()
        if q.strip():
            mask = (
                view["fullName"].str.contains(q, case=False, na=False)
                | view["companyEmail"].str.contains(q, case=False, na=False)
                | view["department"].str.contains(q, case=False, na=False)
            )
            view = view[mask]

        roster = view.head(500).reset_index(drop=True)
        labels = [f"{r['fullName']} — {r['department']}" for _, r in roster.iterrows()]
        if labels:
            pick = st.selectbox(
                "Employee detail",
                range(len(labels)),
                format_func=lambda i: labels[i],
            )
            row = roster.iloc[pick]
            st.markdown("#### " + str(row["fullName"]))
            st.caption(str(row["companyEmail"]))
            d1, d2 = st.columns(2)
            with d1:
                st.write("**Department**", row["department"])
                st.write("**Job title**", row["jobTitle"])
                st.write("**Office**", row["officeLocation"])
                st.write("**Region**", row["region"])
            with d2:
                st.write("**Salary**", f"{row['currentSalary']:,.0f} {row['currentSalaryCurrency']}")
                st.write("**USD salary**", fmt_usd(float(row["usdCurrentSalary"])))
                st.write("**Eligible**", "Yes" if row["eligibility"] else "No")
                st.write(
                    "**Rec. raise**",
                    f"{float(row['recRaisePctMin'])*100:.1f}% – {float(row['recRaisePctMax'])*100:.1f}%",
                )

        show = [
            "fullName",
            "companyEmail",
            "department",
            "jobTitle",
            "currentSalaryCurrency",
            "currentSalary",
            "usdCurrentSalary",
            "eligibility",
            "recBonusPctMin",
            "recBonusPctMax",
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
        st.info("No roster loaded.")
    else:
        stats = compute_dashboard_stats(df)
        glass_section(
            "All departments",
            "Payroll, bonus, and merit pools in USD",
            render_department_table(stats.departments),
        )
        dept = st.selectbox("Drill down", sorted(df["department"].unique()))
        sub = df[df["department"] == dept]
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Headcount", str(len(sub)))
        with c2:
            metric_card("Payroll USD", fmt_usd(sub["usdCurrentSalary"].sum()))
        with c3:
            metric_card(
                "Bonus + raise USD",
                fmt_usd(sub["usdSumOfBonus"].sum() + sub["usdSalaryIncreaseAmt"].sum()),
            )
        st.dataframe(
            sub[
                [
                    "fullName",
                    "jobTitle",
                    "officeLocation",
                    "currentSalary",
                    "currentSalaryCurrency",
                    "usdCurrentSalary",
                    "eligibility",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
