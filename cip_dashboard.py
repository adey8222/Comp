"""Dashboard stats and HTML tables for Streamlit CIP (mirrors loadDashboardStats.ts)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from cip_normalize import load_from_path

# Bundled dataset shipped with the repo for Streamlit Cloud (auto-load on first visit).
BUNDLED_DATA_PATH = Path(__file__).resolve().parent / "data" / "compensation_employee_dataset_updated.xlsx"


@dataclass
class DashboardStats:
    total_employees: int
    eligible_count: int
    total_payroll_usd: float
    total_bonus_usd: float
    total_raise_usd: float
    currencies: list[dict[str, Any]]
    departments: list[dict[str, Any]]


def fmt_usd(n: float) -> str:
    return f"${n:,.0f}"


def fmt_local(n: float) -> str:
    return f"{n:,.0f}"


def compute_dashboard_stats(df: pd.DataFrame) -> DashboardStats:
    if df is None or df.empty:
        return DashboardStats(0, 0, 0.0, 0.0, 0.0, [], [])

    eligible = int(df["eligibility"].sum()) if "eligibility" in df.columns else 0
    payroll = float(df["usdCurrentSalary"].sum())
    bonus = float(df["usdSumOfBonus"].sum()) if "usdSumOfBonus" in df.columns else 0.0
    raise_usd = float(df["usdSalaryIncreaseAmt"].sum()) if "usdSalaryIncreaseAmt" in df.columns else 0.0

    by_cur = (
        df.groupby("currentSalaryCurrency", as_index=False)
        .agg(
            count=("fullName", "count"),
            localSalarySum=("currentSalary", "sum"),
            usdSalarySum=("usdCurrentSalary", "sum"),
        )
        .sort_values("usdSalarySum", ascending=False)
    )
    currencies = [
        {
            "currency": str(r["currentSalaryCurrency"]),
            "count": int(r["count"]),
            "localSalarySum": float(r["localSalarySum"]),
            "usdSalarySum": float(r["usdSalarySum"]),
        }
        for _, r in by_cur.iterrows()
    ]

    by_dept = (
        df.groupby("department", as_index=False)
        .agg(
            headcount=("fullName", "count"),
            payrollUsd=("usdCurrentSalary", "sum"),
            bonusUsd=("usdSumOfBonus", "sum"),
            raiseUsd=("usdSalaryIncreaseAmt", "sum"),
        )
        .sort_values("department")
    )
    departments = [
        {
            "department": str(r["department"]),
            "headcount": int(r["headcount"]),
            "payrollUsd": float(r["payrollUsd"]),
            "bonusUsd": float(r["bonusUsd"]),
            "raiseUsd": float(r["raiseUsd"]),
        }
        for _, r in by_dept.iterrows()
    ]

    return DashboardStats(
        total_employees=len(df),
        eligible_count=eligible,
        total_payroll_usd=payroll,
        total_bonus_usd=bonus,
        total_raise_usd=raise_usd,
        currencies=currencies,
        departments=departments,
    )


def conversion_line(currency: str, count: int, local_sum: float, usd_sum: float) -> str:
    if currency == "USD":
        return f"Already in USD — {fmt_usd(usd_sum)} payroll across {count} people."
    rate = usd_sum / local_sum if local_sum > 0 else 0
    hint = f" (~{rate:.3f} USD per 1 {currency})" if rate > 0 else ""
    return f"Conversion: {fmt_local(local_sum)} {currency} ≈ {fmt_usd(usd_sum)} USD{hint}"


def render_currency_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="muted">No currency rows.</p>'
    body = []
    for r in rows:
        cur = html.escape(r["currency"])
        tip = html.escape(conversion_line(cur, r["count"], r["localSalarySum"], r["usdSalarySum"]))
        body.append(
            f"""<tr>
            <td><span class="cur-pill" title="{tip}">{cur}</span></td>
            <td class="num">{r["count"]}</td>
            <td class="num">{fmt_local(r["localSalarySum"])}</td>
            </tr>"""
        )
    return f"""
    <table class="cip-table">
      <thead><tr>
        <th>Currency</th><th>Headcount</th><th>Local salary sum</th>
      </tr></thead>
      <tbody>{"".join(body)}</tbody>
    </table>
    """


def render_department_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="muted">No department rows.</p>'
    body = []
    for r in rows:
        dept = html.escape(r["department"])
        body.append(
            f"""<tr>
            <td class="dept">{dept}</td>
            <td class="num">{r["headcount"]}</td>
            <td class="num">{fmt_usd(r["payrollUsd"])}</td>
            <td class="num">{fmt_usd(r["bonusUsd"])}</td>
            <td class="num">{fmt_usd(r["raiseUsd"])}</td>
            </tr>"""
        )
    return f"""
    <table class="cip-table">
      <thead><tr>
        <th>Department</th><th>Headcount</th><th>Payroll USD</th>
        <th>Bonus USD</th><th>Raise USD</th>
      </tr></thead>
      <tbody>{"".join(body)}</tbody>
    </table>
    """


def load_bundled_dataset() -> tuple[pd.DataFrame, list[str]]:
    if not BUNDLED_DATA_PATH.is_file():
        return pd.DataFrame(), [f"Bundled data not found: {BUNDLED_DATA_PATH}"]
    return load_from_path(BUNDLED_DATA_PATH)
