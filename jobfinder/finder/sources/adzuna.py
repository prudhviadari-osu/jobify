"""Adzuna source — the broad-discovery layer (DESIGN.md §8).

Adzuna aggregates jobs from many employers. We query it for your medtech
keywords and get back structured results. Two jobs at once:
  1. Add the jobs themselves to the pipeline.
  2. For any result whose apply URL is a Workday URL, auto-register that company
     (discovery.py) so the Workday source polls its full board next run.

Free API: needs an App ID + App Key from https://developer.adzuna.com/ .
Docs: https://developer.adzuna.com/  (search endpoint returns JSON `results`).
"""
from __future__ import annotations

import time
from urllib.parse import quote

import requests

from .. import config
from ..discovery import register_from_url
from ..models import NormalizedJob
from ..workday_tenant import is_workday_url

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
REQUEST_TIMEOUT = 20
RESULTS_PER_PAGE = 50
MAX_PAGES = 3          # keep well under the free-tier daily limit


def _search(keyword: str, page: int, country: str, app_id: str, app_key: str,
            session: requests.Session) -> list[dict]:
    url = API.format(country=country, page=page)
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": RESULTS_PER_PAGE,
        "what": keyword,
        "content-type": "application/json",
    }
    try:
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except (requests.RequestException, ValueError) as exc:
        print(f"    [adzuna] '{keyword}' page {page} failed: {exc}")
        return []


def _to_job(r: dict) -> NormalizedJob:
    company = (r.get("company") or {}).get("display_name", "")
    location = (r.get("location") or {}).get("display_name", "")
    return NormalizedJob(
        source="adzuna",
        source_job_id=str(r.get("id", r.get("redirect_url", ""))),
        company=company,
        title=r.get("title", ""),
        location=location,
        url=r.get("redirect_url", ""),
        description=r.get("description", ""),
        posted_at=r.get("created", ""),
    )


def fetch(keywords: list[str], country: str = "us", delay: float = 0.5) -> list[NormalizedJob]:
    app_id = config.ADZUNA_APP_ID
    app_key = config.ADZUNA_APP_KEY
    if not (app_id and app_key):
        print("  [adzuna] no API key set — skipping. Add ADZUNA_APP_ID / ADZUNA_APP_KEY "
              "to config.py (free key: https://developer.adzuna.com/).")
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "job-application-assistant/0.1 (personal use)"})

    results: dict[str, NormalizedJob] = {}
    discovered = 0
    for kw in keywords:
        print(f"  [adzuna] searching '{kw}' …")
        for page in range(1, MAX_PAGES + 1):
            rows = _search(kw, page, country, app_id, app_key, session)
            if not rows:
                break
            for r in rows:
                job = _to_job(r)
                results[job.job_key] = job
                # Auto-discover Workday companies from apply URLs.
                if is_workday_url(job.url) and register_from_url(job.url):
                    discovered += 1
            if len(rows) < RESULTS_PER_PAGE:
                break
            if delay:
                time.sleep(delay)

    print(f"  [adzuna] found {len(results)} jobs; "
          f"discovered {discovered} new Workday company/ies this run")
    return list(results.values())
