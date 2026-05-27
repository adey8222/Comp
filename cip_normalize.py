"""Spreadsheet normalization for Streamlit CIP (mirrors src/lib/normalize.ts + fx)."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd

CURRENCIES = frozenset({"USD", "ILS", "CAD", "AUD", "EUR", "GBP"})

BASE_RATES_USD_PER_UNIT = {
    "USD": 1.0,
    "ILS": 0.275,
    "CAD": 0.72,
    "AUD": 0.64,
    "EUR": 1.08,
    "GBP": 1.27,
}

HEADER_ALIASES: dict[str, str] = {
    "department": "department",
    "departments": "department",
    "full name": "fullName",
    "email": "companyEmail",
    "company email": "companyEmail",
    "job title": "jobTitle",
    "office location": "officeLocation",
    "office locations": "officeLocation",
    "region": "region",
    "start date": "startDate",
    "employee type": "employeeType",
    "user status": "userStatus",
    "current salary currency": "currentSalaryCurrency",
    "eligibility": "eligibility",
    "current salary": "currentSalary",
    "bonus awarded": "bonusAwardedPct",
    "sum of bonus": "sumOfBonus",
    "salary percentage": "salaryPercentage",
    "salary increase amount": "salaryIncreaseAmount",
    "performance band": "performanceBand",
    "performance score": "performanceBand",
}


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", str(h)).strip().lower()


def map_headers(headers: list[str]) -> list[str]:
    out: list[str] = []
    for h in headers:
        key = HEADER_ALIASES.get(_norm_header(h))
        out.append(key if key else h)
    return out


def _parse_overrides() -> dict[str, float]:
    raw = os.environ.get("FX_RATES_STUB", "").strip()
    if not raw and hasattr(__import__("streamlit"), "secrets"):
        try:
            import streamlit as st

            raw = str(st.secrets.get("FX_RATES_STUB", "") or "").strip()
        except Exception:
            raw = ""
    out: dict[str, float] = {}
    for part in raw.split(","):
        if "=" not in part:
            continue
        k, v = (p.strip() for p in part.split("=", 1))
        try:
            out[k.upper()] = float(v)
        except ValueError:
            continue
    return out


def usd_per_unit(currency: str) -> float:
    key = currency.upper()
    overrides = _parse_overrides()
    if key in overrides:
        return overrides[key]
    return BASE_RATES_USD_PER_UNIT.get(key, 1.0)


def convert_to_usd(amount: float, currency: str) -> float:
    if currency.upper() == "USD":
        return amount
    return amount * usd_per_unit(currency)


def excel_serial_to_date(serial: float) -> datetime:
    utc = round((serial - 25569) * 86400)
    return datetime.fromtimestamp(utc, tz=timezone.utc)


def _parse_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v or "").strip().lower()
    return s in ("true", "yes", "1", "eligible")


def _parse_number(v: Any) -> float:
    if isinstance(v, (int, float)) and pd.notna(v):
        return float(v)
    s = str(v or "").replace(",", "").strip()
    return float(s)


def _parse_date(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, (int, float)) and pd.notna(v):
        n = float(v)
        if 20000 < n < 60000:
            return excel_serial_to_date(n)
        return datetime.fromtimestamp(n / 1000 if n > 1e12 else n, tz=timezone.utc)
    s = str(v or "").strip()
    ts = pd.to_datetime(s, errors="coerce")
    if pd.notna(ts):
        return ts.to_pydatetime()
    n = _parse_number(v)
    if 20000 < n < 60000:
        return excel_serial_to_date(n)
    raise ValueError(f"Invalid date: {v!r}")


def _parse_currency(v: Any) -> str:
    s = str(v or "").strip().upper()
    if s not in CURRENCIES:
        raise ValueError(f"Invalid currency: {v!r}")
    return s


def _close(a: float, b: float, scale: float) -> bool:
    return abs(a - b) < max(1.0, scale * 1e-6)


def _reconcile_salary_increase(
    current_salary: float, salary_pct: float, salary_increase_field: float
) -> tuple[float, float]:
    expected_inc = current_salary * salary_pct
    expected_new = current_salary * (1 + salary_pct)
    if _close(salary_increase_field, expected_new, current_salary) and not _close(
        salary_increase_field, expected_inc, current_salary
    ):
        return salary_increase_field - current_salary, salary_pct
    return salary_increase_field, salary_pct


def _tenure_years(start: datetime, as_of: datetime | None = None) -> float:
    as_of = as_of or datetime.now(tz=timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return (as_of - start).total_seconds() / (365.25 * 24 * 3600)


def recommend(row: dict[str, Any]) -> dict[str, float]:
    perf = str(row.get("performanceBand") or "AVERAGE").upper()
    years = _tenure_years(row["startDate"])
    rec_raise_min, rec_raise_max = 0.03, 0.05
    if perf == "HIGH":
        rec_raise_min, rec_raise_max = 0.05, 0.10
    elif perf == "LOW":
        rec_raise_min, rec_raise_max = 0.0, 0.02
    rec_bonus_min, rec_bonus_max = 0.0, 0.05
    if perf == "HIGH" and years > 1:
        rec_bonus_min, rec_bonus_max = 0.10, 0.20
    elif perf == "HIGH":
        rec_bonus_min, rec_bonus_max = 0.05, 0.10
    if not row.get("eligibility"):
        return {
            "recBonusPctMin": 0.0,
            "recBonusPctMax": 0.0,
            "recRaisePctMin": 0.0,
            "recRaisePctMax": 0.0,
        }
    return {
        "recBonusPctMin": rec_bonus_min,
        "recBonusPctMax": rec_bonus_max,
        "recRaisePctMin": rec_raise_min,
        "recRaisePctMax": rec_raise_max,
    }


def normalize_raw_row(raw: dict[str, Any]) -> dict[str, Any]:
    current_salary = _parse_number(raw.get("currentSalary"))
    bonus_awarded_pct = _parse_number(raw.get("bonusAwardedPct"))
    salary_pct = _parse_number(raw.get("salaryPercentage"))
    salary_inc = _parse_number(raw.get("salaryIncreaseAmount"))
    salary_inc, salary_pct = _reconcile_salary_increase(current_salary, salary_pct, salary_inc)
    currency = _parse_currency(raw.get("currentSalaryCurrency"))
    row = {
        "department": str(raw.get("department") or "").strip(),
        "fullName": str(raw.get("fullName") or "").strip(),
        "companyEmail": str(raw.get("companyEmail") or "").strip(),
        "jobTitle": str(raw.get("jobTitle") or "").strip(),
        "officeLocation": str(raw.get("officeLocation") or "").strip(),
        "region": str(raw.get("region") or "").strip(),
        "startDate": _parse_date(raw.get("startDate")),
        "employeeType": str(raw.get("employeeType") or "").strip(),
        "userStatus": str(raw.get("userStatus") or "").strip(),
        "currentSalaryCurrency": currency,
        "eligibility": _parse_bool(raw.get("eligibility")),
        "currentSalary": current_salary,
        "bonusAwardedPct": bonus_awarded_pct,
        "sumOfBonus": _parse_number(raw.get("sumOfBonus")),
        "salaryPercentage": salary_pct,
        "salaryIncreaseAmount": salary_inc,
        "performanceBand": (
            str(raw.get("performanceBand")).strip()
            if raw.get("performanceBand") is not None
            and not (isinstance(raw.get("performanceBand"), float) and pd.isna(raw.get("performanceBand")))
            and str(raw.get("performanceBand")).strip() != ""
            else None
        ),
    }
    if not row["department"] or not row["fullName"] or "@" not in row["companyEmail"]:
        raise ValueError("Missing required fields (department, name, or email)")
    row["usdCurrentSalary"] = convert_to_usd(current_salary, currency)
    row["usdSumOfBonus"] = convert_to_usd(row["sumOfBonus"], currency)
    row["usdSalaryIncreaseAmt"] = convert_to_usd(salary_inc, currency)
    row.update(recommend(row))
    return row


def load_and_normalize(uploaded: Any) -> tuple[pd.DataFrame, list[str]]:
    name = (uploaded.name or "").lower()
    if name.endswith(".csv"):
        raw = pd.read_csv(uploaded)
    else:
        raw = pd.read_excel(uploaded, engine="openpyxl")
    mapped = map_headers(list(raw.columns))
    raw.columns = mapped
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    for i, r in raw.iterrows():
        try:
            rows.append(normalize_raw_row(r.to_dict()))
        except Exception as e:
            errors.append(f"Row {int(i) + 2}: {e}")
    if not rows:
        return pd.DataFrame(), errors
    df = pd.DataFrame(rows)
    return df, errors
