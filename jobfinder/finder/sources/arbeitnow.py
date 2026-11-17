"""Arbeitnow source — a FREE, no-key discovery feed (replaces Adzuna's role).

Arbeitnow publishes a public job-board feed with no authentication:
    https://www.arbeitnow.com/api/job-board-api
Response: {"data": [ {title, company_name, location, remote, url, tags,
            job_types, description, created_at, slug}, ... ], "links": {next}}

Honest scope: Arbeitnow is Europe/DACH-leaning and tech-heavy, so it is a
SUPPLEMENT for US medtech, not a primary source. Its value here is twofold:
  1. it's genuinely free with no key and no card, and
  2. any job whose `url` is a *.myworkdayjobs.com link feeds the same Workday
     auto-discovery we built for Adzuna (discovery.py).

We filter client-side to keywords (the feed has no server-side search).
"""
from __future__ import annotations

import time

import requests

from ..discovery import register_from_url
from ..models import NormalizedJob
from ..workday_tenant import is_workday_url

FEED_URL = "https://www.arbeitnow.com/api/job-board-api"
REQUEST_TIMEOUT = 20
MAX_PAGES = 5          # feed is paginated via links.next


def _matches(row: dict, keywords: list[str]) -> bool:
    if not keywords:
        return True
    hay = " ".join([
        row.get("title", ""),
        row.get("company_name", ""),
        " ".join(row.get("tags", []) or []),
        row.get("description", "")[:500],
    ]).lower()
    return any(kw.lower() in hay for kw in keywords)


def _to_job(row: dict) -> NormalizedJob:
    return NormalizedJob(
        source="arbeitnow",
        source_job_id=row.get("slug", row.get("url", "")),
        company=row.get("company_name", ""),
        title=row.get("title", ""),
        location=row.get("location", ""),
        remote=bool(row.get("remote")),
        url=row.get("url", ""),
        description=row.get("description", ""),
        posted_at=str(row.get("created_at", "")),
    )


def fetch(keywords: list[str], delay: float = 0.5) -> list[NormalizedJob]:
    session = requests.Session()
    session.headers.update({"User-Agent": "job-application-assistant/0.1 (personal use)"})

    results: dict[str, NormalizedJob] = {}
    discovered = 0
    url = FEED_URL
    pages = 0

    while url and pages < MAX_PAGES:
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"    [arbeitnow] request failed: {exc}")
            break

        rows = payload.get("data", []) or []
        for row in rows:
            if not _matches(row, keywords):
                continue
            job = _to_job(row)
            results[job.job_key] = job
            if is_workday_url(job.url) and register_from_url(job.url):
                discovered += 1

        url = (payload.get("links") or {}).get("next")
        pages += 1
        if url and delay:
            time.sleep(delay)

    print(f"  [arbeitnow] {len(results)} jobs matched your keywords; "
          f"discovered {discovered} new Workday company/ies")
    return list(results.values())
