"""Greenhouse source — free, no-key, per-company public Job Board API.

One call returns a company's whole board:
    GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true

No auth. Each job has: id, title, location.name, absolute_url, updated_at, and
(with content=true) an HTML description in `content`. The {slug} is the board
token — the last path segment of boards.greenhouse.io/<slug> — which is often
NOT the company's marketing name, so it's configured per-company.

Docs: https://docs.greenhouse.io/job-board
Like Workday, there is no cross-company search: you list the companies.
"""
from __future__ import annotations

import html
import re
import time

import requests

from ..models import NormalizedJob

BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
REQUEST_TIMEOUT = 20
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    # Unescape entities FIRST (&lt;p&gt; -> <p>), then strip the resulting tags,
    # then unescape again for any entities that were inside the text (&amp; etc.).
    unescaped = html.unescape(text)
    stripped = _TAG_RE.sub(" ", unescaped)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def _matches(job: NormalizedJob, keywords: list[str]) -> bool:
    if not keywords:
        return True
    hay = f"{job.title} {job.description[:600]}".lower()
    return any(kw.lower() in hay for kw in keywords)


def _fetch_board(company: dict, keywords: list[str], session: requests.Session) -> list[NormalizedJob]:
    slug = company["slug"]
    name = company.get("name", slug)
    try:
        resp = session.get(BOARD_URL.format(slug=slug),
                           params={"content": "true"}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"    [greenhouse:{name}] request failed: {exc}")
        return []

    out = []
    for j in data.get("jobs", []) or []:
        job = NormalizedJob(
            source="greenhouse",
            source_job_id=f"{slug}:{j.get('id', '')}",
            company=name,
            title=j.get("title", ""),
            location=(j.get("location") or {}).get("name", ""),
            url=j.get("absolute_url", ""),
            description=_strip_html(j.get("content", "")),
            posted_at=j.get("updated_at", ""),
        )
        if _matches(job, keywords):
            out.append(job)
    return out


def fetch(keywords: list[str], companies: list[dict], delay: float = 0.5) -> list[NormalizedJob]:
    if not companies:
        print("  [greenhouse] no companies configured — add {'name','slug'} entries "
              "to GREENHOUSE_COMPANIES in config.py.")
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "job-application-assistant/0.1 (personal use)"})

    results: dict[str, NormalizedJob] = {}
    for company in companies:
        print(f"  [greenhouse] reading {company.get('name', company['slug'])} board …")
        for job in _fetch_board(company, keywords, session):
            results[job.job_key] = job
        if delay:
            time.sleep(delay)

    print(f"  [greenhouse] {len(results)} jobs matched your keywords")
    return list(results.values())
