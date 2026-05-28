"""Import preview + merge-by-email commit (mirrors Next.js import API)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from cip_normalize import _rewind_upload, load_and_normalize


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, (pd.Timestamp,)):
            out[k] = v.isoformat()
        elif pd.isna(v):
            out[k] = None
        else:
            out[k] = v
    return out


def _parse_error_strings(errs: list[str]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for e in errs:
        if e.startswith("Row "):
            head, _, rest = e.partition(": ")
            try:
                idx = int(head.replace("Row ", "").strip())
            except ValueError:
                idx = 0
            parsed.append({"rowIndex": idx, "message": rest or e})
        else:
            parsed.append({"rowIndex": 0, "message": e})
    return parsed


def preview_import(uploaded: Any) -> dict[str, Any]:
    """Same shape as POST /api/import/preview JSON."""
    _rewind_upload(uploaded)
    df, errs = load_and_normalize(uploaded)
    preview = [_serialize_row(r) for r in df.head(25).to_dict(orient="records")]
    return {
        "fileName": getattr(uploaded, "name", "upload"),
        "okCount": len(df),
        "errorCount": len(errs),
        "errors": _parse_error_strings(errs)[:50],
        "preview": preview,
    }


def commit_merge_by_email(
    existing: pd.DataFrame | None,
    uploaded: Any,
) -> tuple[pd.DataFrame, str, list[str]]:
    """
    Merge upload into roster by company email (same rules as /api/import/commit).
    Rows not in the file are left unchanged.
    """
    _rewind_upload(uploaded)
    new_df, parse_errs = load_and_normalize(uploaded)
    if new_df.empty:
        err_msg = "No valid rows"
        if parse_errs:
            err_msg += f" ({len(parse_errs)} parse errors)"
        return existing if existing is not None else pd.DataFrame(), err_msg, parse_errs

    keys = new_df["companyEmail"].str.strip().str.lower()
    dupes = keys[keys.duplicated(keep=False)]
    if len(dupes) > 0:
        return (
            existing if existing is not None else pd.DataFrame(),
            f"Duplicate email in file: {dupes.iloc[0]}",
            parse_errs,
        )

    new_df = new_df.copy()
    new_df["_email_key"] = keys

    if existing is None or existing.empty:
        total = len(new_df)
        out = new_df.drop(columns=["_email_key"])
        msg = (
            f"Merge complete: 0 updated, {total} new (0 other employees unchanged). "
            f"Total roster: {total}."
        )
        return out, msg, parse_errs

    existing = existing.copy()
    existing["_email_key"] = existing["companyEmail"].str.strip().str.lower()
    file_keys = set(new_df["_email_key"])
    unchanged_count = int((~existing["_email_key"].isin(file_keys)).sum())
    kept = existing[~existing["_email_key"].isin(file_keys)].drop(columns=["_email_key"])

    existing_keys = set(existing["_email_key"])
    created = int((~new_df["_email_key"].isin(existing_keys)).sum())
    updated = len(new_df) - created

    merged = pd.concat([kept, new_df.drop(columns=["_email_key"])], ignore_index=True)
    total = len(merged)
    msg = (
        f"Merge complete: {updated} updated, {created} new "
        f"({unchanged_count} other employees unchanged). Total roster: {total}."
    )
    return merged, msg, parse_errs
