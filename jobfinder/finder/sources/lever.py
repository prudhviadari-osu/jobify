"""Lever source — free, no-key, per-company public Postings API.

    GET https://api.lever.co/v0/postings/{slug}?mode=json&skip=N&limit=50

No auth. Paginate with skip/limit (50/page) until an empty page. Each posting
has: id, text (title), hostedUrl, applyUrl, categories (team/department/location),
workplaceType, country, and a plain-text `description`/`descriptionPlain`.

EU-hosted boards (jobs.eu.lever.co) use api.eu.lever.co — set "eu": true.
Docs: https://github.com/lever/postings-api
Like Workday/Greenhouse, no cross-company search: you list the companies.
"""
from __future__ import annotations

import time

import requests

from ..models import NormalizedJob

US_HOST = "https://api.lever.co/v0/postings/{slug}"
EU_HOST = "https://api.eu.lever.co/v0/postings/{slug}"
PAGE_SIZE = 50
REQUEST_TIMEOUT = 20


def _matches(job: NormalizedJob, keywords: list[str]) -> bool:
    if not keywords:
        return True
    hay = f"{job.title} {job.description[:600]}".lower()
    return any(kw.lower() in hay for kw in keywords)


def _location(posting: dict) -> str:
    cats = posting.get("categories") or {}
    # Lever exposes location in categories.location (and sometimes allLocations).
    loc = cats.get("location") or ""
    if not loc and cats.get("allLocations"):
        loc = ", ".join(cats["allLocations"])
    return loc


def _to_job(slug: str, name: str, p: dict) -> NormalizedJob:
    workplace = (p.get("workplaceType") or "").lower()
    return NormalizedJob(
        source="lever",
        source_job_id=f"{slug}:{p.get('id', '')}",
        company=name,
        title=p.get("text", ""),
        location=_location(p),
        remote=workplace == "remote",
        url=p.get("hostedUrl", p.get("applyUrl", "")),
        description=p.get("descriptionPlain", p.get("description", "")),
        posted_at=str(p.get("createdAt", "")),
    )


def _fetch_board(company: dict, keywords: list[str], session: requests.Session,
                 delay: float) -> list[NormalizedJob]:
    slug = company["slug"]
    name = company.get("name", slug)
    host = EU_HOST if company.get("eu") else US_HOST
    out: list[NormalizedJob] = []
    skip = 0

    while True:
        try:
            resp = session.get(host.format(slug=slug),
                               params={"mode": "json", "skip": skip, "limit": PAGE_SIZE},
                               timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            rows = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"    [lever:{name}] request failed at skip {skip}: {exc}")
            break

        if not rows:
            break
        for p in rows:
            job = _to_job(slug, name, p)
            if _matches(job, keywords):
                out.append(job)
        if len(rows) < PAGE_SIZE:
            break
        skip += PAGE_SIZE
        if delay:
            time.sleep(delay)
    return out


def fetch(keywords: list[str], companies: list[dict], delay: float = 0.5) -> list[NormalizedJob]:
    if not companies:
        print("  [lever] no companies configured — add {'name','slug'[,'eu':true]} "
              "entries to LEVER_COMPANIES in config.py.")
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "job-application-assistant/0.1 (personal use)"})

    results: dict[str, NormalizedJob] = {}
    for company in companies:
        print(f"  [lever] reading {company.get('name', company['slug'])} board …")
        for job in _fetch_board(company, keywords, session, delay):
            results[job.job_key] = job

    print(f"  [lever] {len(results)} jobs matched your keywords")
    return list(results.values())
