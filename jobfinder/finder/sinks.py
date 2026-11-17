"""Where found jobs get written. Two sinks, same interface:

    write(jobs) -> (added_count, skipped_duplicate_count)

Both dedupe on job_key against whatever is already stored, so re-runs only add
genuinely new jobs (DESIGN.md §4).
"""
from __future__ import annotations

import csv
import os
from typing import Iterable

from . import config
from .models import FIELDNAMES, NormalizedJob


# --------------------------------------------------------------------------- #
# CSV sink (default, zero setup)
# --------------------------------------------------------------------------- #
def _existing_keys_csv(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        return {row["job_key"] for row in csv.DictReader(f) if row.get("job_key")}


def write_csv(jobs: Iterable[NormalizedJob], path: str = None) -> tuple[int, int]:
    path = path or config.CSV_PATH
    existing = _existing_keys_csv(path)
    new_rows = []
    skipped = 0
    for job in jobs:
        if job.job_key in existing:
            skipped += 1
            continue
        existing.add(job.job_key)
        new_rows.append(job.to_row())

    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)
    return len(new_rows), skipped


# --------------------------------------------------------------------------- #
# Google Sheets sink (free; activated with --sink sheets)
# --------------------------------------------------------------------------- #
def write_sheets(jobs: Iterable[NormalizedJob]) -> tuple[int, int]:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise SystemExit(
            "Google Sheets output needs extra packages. Install them with:\n"
            "    pip install gspread google-auth\n"
            f"(import error: {exc})"
        )

    if not config.GOOGLE_SHEET_ID:
        raise SystemExit("Set GOOGLE_SHEET_ID in config.py (see README) to use the sheets sink.")
    if not os.path.exists(config.GOOGLE_CREDS_PATH):
        raise SystemExit(
            f"Missing {config.GOOGLE_CREDS_PATH}. Download your service-account key "
            "and save it there (see README)."
        )

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(config.GOOGLE_CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    sh = client.open_by_key(config.GOOGLE_SHEET_ID)

    try:
        ws = sh.worksheet(config.GOOGLE_WORKSHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=config.GOOGLE_WORKSHEET, rows=1000, cols=len(FIELDNAMES))
        ws.append_row(FIELDNAMES)

    all_values = ws.get_all_values()
    if not all_values:
        ws.append_row(FIELDNAMES)
        existing = set()
    else:
        header = all_values[0]
        key_idx = header.index("job_key") if "job_key" in header else 0
        existing = {r[key_idx] for r in all_values[1:] if len(r) > key_idx}

    new_rows = []
    skipped = 0
    for job in jobs:
        if job.job_key in existing:
            skipped += 1
            continue
        existing.add(job.job_key)
        row = job.to_row()
        new_rows.append([row[c] for c in FIELDNAMES])

    if new_rows:
        ws.append_rows(new_rows, value_input_option="RAW")
    return len(new_rows), skipped


def get_sink(name: str):
    return {"csv": write_csv, "sheets": write_sheets}[name]
