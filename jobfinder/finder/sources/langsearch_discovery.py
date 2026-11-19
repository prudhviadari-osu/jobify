"""LangSearch-powered company DISCOVERY (not a job feed).

Fixes the real gap: Workday/Greenhouse have no directory, so we couldn't find
*which* companies to search without hand-listing them. LangSearch is a free web
search API (langsearch.com) — we query it scoped to ATS domains, pull the company
career URLs out of the results, and auto-register them via discovery.register.

This does NOT return jobs. It grows the list of companies that the Workday /
Greenhouse sources then search directly (those remain the real job feed, because
their per-company APIs give clean structured postings; web-search snippets don't).

Free, needs an API key (LANGSEARCH_API_KEY). Only your search *keywords* leave the
machine — no profile/resume data. If no key is set, this source simply skips.

API: POST https://api.langsearch.com/v1/web-search
  body {query, count<=50, includeDomains:[...]}
  results at data.webPages.value[] -> {name, url, snippet}
"""
from __future__ import annotations

import time

import requests

from .. import config
from ..discovery import register_from_url
from ..workday_tenant import is_workday_url

API = "https://api.langsearch.com/v1/web-search"
REQUEST_TIMEOUT = 30
# ATS domains we try to discover companies on (Workday first; others parse-ready).
DISCOVERY_DOMAINS = ["myworkdayjobs.com"]


def discover(keywords: list[str], delay: float = 0.5) -> int:
    """Search LangSearch for ATS career pages matching the keywords and register
    any new Workday companies found. Returns the count of newly-added companies."""
    api_key = getattr(config, "LANGSEARCH_API_KEY", "")
    if not api_key:
        print("  [langsearch] no API key set — skipping discovery. Add "
              "LANGSEARCH_API_KEY to config.py (free key: https://langsearch.com/dashboard).")
        return 0

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "job-application-assistant/0.1 (personal use)",
    })

    discovered = 0
    for kw in keywords:
        for domain in DISCOVERY_DOMAINS:
            query = f"{kw} jobs"
            try:
                resp = session.post(API, json={
                    "query": query,
                    "count": 20,
                    "includeDomains": [domain],
                }, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                payload = resp.json()
            except (requests.RequestException, ValueError) as exc:
                print(f"    [langsearch] '{query}' on {domain} failed: {exc}")
                continue

            if str(payload.get("code")) not in ("200", "None", ""):
                # LangSearch signals errors in the body code field.
                if payload.get("code") and str(payload["code"]) != "200":
                    print(f"    [langsearch] API error: {payload.get('message','?')}")
                    continue

            pages = (((payload.get("data") or {}).get("webPages") or {}).get("value")) or []
            for page in pages:
                url = page.get("url", "")
                if is_workday_url(url) and register_from_url(url):
                    discovered += 1
            if delay:
                time.sleep(delay)

    print(f"  [langsearch] discovered {discovered} new Workday company/ies via web search")
    return discovered
