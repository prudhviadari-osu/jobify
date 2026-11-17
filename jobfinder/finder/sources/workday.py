"""Workday source — reads jobs from a company's own public JSON endpoint.

Why this works (DESIGN.md §8): every myworkdayjobs.com careers site is a
single-page app whose job list is loaded from a plain JSON endpoint. We call
that endpoint directly — no key, no login, no browser:

    POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
    body: {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "..."}

Each response holds up to 20 `jobPostings` (title, locationsText, postedOn,
externalPath, bulletFields with the requisition id), plus `total`. We page via
`offset`. Known quirks we guard against:
  - up to 20 per page,
  - a ~2,000-result ceiling per query,
  - an offset that can loop past the end (so we stop when a page repeats or is short).

The real apply URL is:
    https://{tenant}.{dc}.myworkdayjobs.com/{site}{externalPath}
"""
from __future__ import annotations

import time
from typing import Iterable

import requests

from ..models import NormalizedJob

PAGE_SIZE = 20
RESULT_CEILING = 2000           # Workday stops returning new jobs past ~this
REQUEST_TIMEOUT = 20


def _base(company: dict) -> str:
    return f"https://{company['tenant']}.{company['dc']}.myworkdayjobs.com"


def _endpoint(company: dict) -> str:
    return f"{_base(company)}/wday/cxs/{company['tenant']}/{company['site']}/jobs"


def _apply_url(company: dict, external_path: str) -> str:
    site = company["site"]
    if not external_path:
        return f"{_base(company)}/{site}"
    return f"{_base(company)}/{site}{external_path}"


def _req_id(posting: dict) -> str:
    """The requisition id lives in bulletFields (usually the last entry)."""
    bullets = posting.get("bulletFields") or []
    if bullets:
        return str(bullets[-1])
    # Fall back to the path, which is unique per posting.
    return posting.get("externalPath", posting.get("title", ""))


def _fetch_company(
    company: dict,
    search_text: str,
    session: requests.Session,
    delay: float,
) -> Iterable[NormalizedJob]:
    endpoint = _endpoint(company)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    offset = 0
    seen_paths: set[str] = set()

    while offset < RESULT_CEILING:
        payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": search_text}
        try:
            resp = session.post(endpoint, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"    [workday:{company['name']}] request failed at offset {offset}: {exc}")
            return

        postings = data.get("jobPostings") or []
        if not postings:
            return

        new_this_page = 0
        for p in postings:
            path = p.get("externalPath", "")
            if path in seen_paths:        # offset looped — stop
                continue
            seen_paths.add(path)
            new_this_page += 1
            yield NormalizedJob(
                source="workday",
                source_job_id=f"{company['tenant']}:{_req_id(p)}",
                company=company["name"],
                title=p.get("title", ""),
                location=p.get("locationsText", ""),
                url=_apply_url(company, path),
                posted_at=p.get("postedOn", ""),
                description="",   # full JD fetched later (Phase 2) only for relevant jobs
            )

        # Stop conditions: short page (end) or nothing new (loop).
        if len(postings) < PAGE_SIZE or new_this_page == 0:
            return

        offset += PAGE_SIZE
        if delay:
            time.sleep(delay)


def fetch(keywords: list[str], companies: list[dict], delay: float = 0.5) -> list[NormalizedJob]:
    """Search every seed company for every keyword; return a deduped list."""
    if not companies:
        print("  [workday] no companies configured — add entries to WORKDAY_COMPANIES "
              "in config.py (use `python -m finder.resolve_workday <careers-url>` to get them).")
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "job-application-assistant/0.1 (personal use)"})

    results: dict[str, NormalizedJob] = {}
    for company in companies:
        print(f"  [workday] searching {company['name']} …")
        for kw in keywords:
            for job in _fetch_company(company, kw, session, delay):
                results[job.job_key] = job   # dedup across keywords
    print(f"  [workday] found {len(results)} unique postings across seed companies")
    return list(results.values())
