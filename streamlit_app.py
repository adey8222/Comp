"""
Compensation Intelligence Platform — Streamlit edition.

Bundled data loads automatically on first visit (data/compensation_employee_dataset_updated.xlsx).
Deploy: streamlit_app.py + requirements.txt + cip_normalize.py + cip_dashboard.py + data/*.xlsx
"""

from __future__ import annotations

import html as html_lib
import io
import json

import pandas as pd
import streamlit as st

from cip_dashboard import (
    BUNDLED_DATA_PATH,
    compute_dashboard_stats,
    fmt_usd,
    load_bundled_dataset,
    render_currency_table,
    render_department_employees_table,
    render_department_table,
    render_metric_row,
)
from cip_import import commit_merge_by_email, preview_import

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
.metric-row {
    display: grid; gap: 1rem; margin-bottom: 1.25rem;
}
.metric-row-3 { grid-template-columns: repeat(3, 1fr); }
.metric-row-5 { grid-template-columns: repeat(5, 1fr); }
@media (max-width: 1100px) {
    .metric-row-5 { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
    .metric-row-3, .metric-row-5 { grid-template-columns: 1fr; }
}
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
.dept-filter-panel {
    padding: 1.25rem 1.5rem; margin-bottom: 1.25rem;
    border: 1px solid rgba(255,255,255,0.08); border-radius: 20px;
    background: rgba(15,23,42,0.5);
}
.table-scroll { overflow-x: auto; }
.cip-table-wide { min-width: 1100px; font-size: 0.8125rem; }
.cip-table .name { color: #67e8f9; font-weight: 500; }
.cip-table .email { color: #71717a; font-size: 0.75rem; margin-top: 0.15rem; }
.badge {
    border-radius: 9999px; padding: 0.15rem 0.5rem;
    font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
}
.badge-yes { background: rgba(16,185,129,0.15); color: #6ee7b7; }
.badge-no { background: rgba(100,116,139,0.15); color: #94a3b8; }
.muted-cell { color: #71717a; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0891b2, #6366f1);
    border: 1px solid rgba(34, 211, 238, 0.35); color: #f8fafc;
}
div[data-testid="stDataFrame"] { border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; }
.import-ingress {
    padding: 1.5rem; margin-bottom: 1rem;
    border: 1px solid rgba(255,255,255,0.08); border-radius: 20px;
    background: rgba(15,23,42,0.55);
}
.import-ingress h2 { margin: 0 0 0.5rem; font-size: 1.125rem; color: #fafafa; }
.import-ingress p { margin: 0; color: #a1a1aa; font-size: 0.875rem; line-height: 1.6; }
.import-ingress strong { color: #e4e4e7; }
div[data-testid="stFileUploader"] {
    padding: 2rem 1.5rem !important; margin-bottom: 1rem !important;
    border: 2px dashed rgba(34,211,238,0.25) !important;
    border-radius: 20px !important;
    background: rgba(15,23,42,0.35) !important;
}
.import-message {
    padding: 0.85rem 1.25rem; margin-bottom: 1rem;
    border: 1px solid rgba(34,211,238,0.2); border-radius: 16px;
    background: rgba(15,23,42,0.55); color: #a5f3fc; font-size: 0.875rem;
}
.import-preview {
    max-height: 520px; overflow: auto; padding: 1.25rem;
    border: 1px solid rgba(255,255,255,0.08); border-radius: 20px;
    background: rgba(15,23,42,0.55);
    font-family: ui-monospace, monospace; font-size: 0.75rem;
    line-height: 1.6; color: #a1a1aa; white-space: pre-wrap;
}
div[data-testid="stFileUploader"] section {
    border: none !important; padding: 0 !important;
}
div[data-testid="stFileUploader"] label p {
    color: #a1a1aa !important; font-size: 0.8rem !important;
}
</style>
"""

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


def init_session() -> None:
    defaults = {
        "employees": None,
        "import_errors": [],
        "data_source": None,
        "selected_employee_idx": 0,
        "dept_focus": None,
        "import_message": None,
        "import_preview": None,
        "import_file_sig": None,
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


def show_html(html: str) -> None:
    """Render HTML reliably (st.columns breaks unsafe_allow_html on markdown)."""
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def glass_section(title: str, subtitle: str, body_html: str) -> None:
    show_html(
        f"""
        <div class="glass-section">
            <div class="glass-section-head">
                <h3>{html_lib.escape(title)}</h3>
                <p>{html_lib.escape(subtitle)}</p>
            </div>
            <div class="glass-section-body">{body_html}</div>
        </div>
        """
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
        show_html(
            render_metric_row(
                [
                    ("Total employees", f"{stats.total_employees:,}", "active cycle"),
                    ("Eligible", f"{stats.eligible_count:,}", "flagged in source"),
                    ("Payroll (USD)", fmt_usd(stats.total_payroll_usd), "normalized"),
                    (
                        "Bonus + raises (USD)",
                        fmt_usd(stats.total_bonus_usd + stats.total_raise_usd),
                        "normalized",
                    ),
                    ("Departments", str(len(stats.departments)), "unique"),
                ],
                columns=5,
            )
        )

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
    show_html(
        """
        <div class="import-ingress">
            <h2>Data ingress</h2>
            <p>
                Drop CSV / XLSX. Headers remap automatically.
                <strong>Commit merges</strong> by <strong>company email</strong>:
                only people in your file are created or updated; everyone else stays as-is.
            </p>
        </div>
        """
    )

    up = st.file_uploader(
        "Choose file",
        type=["csv", "xls", "xlsx"],
        label_visibility="visible",
        key="import_file",
    )

    if up is not None:
        sig = (up.name, up.size)
        if st.session_state.import_file_sig != sig:
            with st.spinner("Previewing…"):
                try:
                    prev = preview_import(up)
                    st.session_state.import_preview = prev
                    st.session_state.import_file_sig = sig
                    st.session_state.import_message = (
                        f"Preview OK: {prev['okCount']} rows, {prev['errorCount']} errors"
                    )
                except Exception as ex:
                    st.session_state.import_preview = None
                    st.session_state.import_message = str(ex)

        commit = st.button("Commit to database", type="primary", use_container_width=False)
        if commit:
            with st.spinner("Committing…"):
                merged, msg, errs = commit_merge_by_email(st.session_state.employees, up)
            if merged is not None and not merged.empty and "Merge complete" in msg:
                st.session_state.employees = merged
                st.session_state.data_source = "upload"
                st.session_state.import_errors = errs
                st.session_state.import_message = msg
                st.rerun()
            else:
                st.session_state.import_message = msg
                st.session_state.import_errors = errs
    else:
        if st.session_state.import_file_sig is not None:
            st.session_state.import_file_sig = None
            st.session_state.import_preview = None

    if st.session_state.import_message:
        show_html(
            f'<div class="import-message">{html_lib.escape(st.session_state.import_message)}</div>'
        )

    prev = st.session_state.import_preview
    if prev:
        preview_json = json.dumps(
            {
                "fileName": prev.get("fileName"),
                "okCount": prev.get("okCount"),
                "errorCount": prev.get("errorCount"),
                "errors": prev.get("errors"),
                "preview": prev.get("preview"),
            },
            indent=2,
            default=str,
        )
        show_html(f'<pre class="import-preview">{html_lib.escape(preview_json)}</pre>')

    with st.expander("Advanced — reset or clear roster"):
        st.caption(
            "Bundled data loads automatically on startup. Use these only if you need to "
            "discard uploads and return to the repo dataset."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Reset to bundled dataset", use_container_width=True):
                st.session_state.employees = cached_bundled_employees()
                st.session_state.data_source = "bundled"
                st.session_state.import_errors = []
                st.session_state.import_message = "Restored bundled dataset."
                st.session_state.import_preview = None
                st.rerun()
        with c2:
            if st.button("Clear all data", use_container_width=True):
                st.session_state.employees = None
                st.session_state.data_source = None
                st.session_state.import_message = "Roster cleared."
                st.session_state.import_preview = None
                st.rerun()

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
    if df is None or df.empty:
        st.info("No roster loaded.")
    else:
        depts = sorted(df["department"].unique())
        if st.session_state.dept_focus not in depts:
            st.session_state.dept_focus = depts[0]

        with st.form("dept_filter", border=False):
            fc1, fc2 = st.columns([5, 1])
            with fc1:
                picked = st.selectbox(
                    "Department",
                    depts,
                    index=depts.index(st.session_state.dept_focus),
                )
            with fc2:
                st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Focus", type="primary", use_container_width=True)
        if submitted:
            st.session_state.dept_focus = picked
            st.rerun()

        dept = st.session_state.dept_focus
        sub = df[df["department"] == dept].sort_values("fullName")
        payroll = float(sub["usdCurrentSalary"].sum())
        bonus_raise = float(sub["usdSumOfBonus"].sum() + sub["usdSalaryIncreaseAmt"].sum())

        show_html(
            render_metric_row(
                [
                    ("Headcount", str(len(sub)), None),
                    ("Payroll USD", fmt_usd(payroll), None),
                    ("Bonus + raise USD", fmt_usd(bonus_raise), None),
                ],
                columns=3,
            )
        )

        n = len(sub)
        emp_label = f"{n} employee{'s' if n != 1 else ''} in this department"
        glass_section(
            dept,
            emp_label,
            render_department_employees_table(sub),
        )
