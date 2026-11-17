"""Helper: turn a Workday careers URL into the tenant/dc/site config entry.

Usage:
    python -m finder.resolve_workday https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers

It parses the URL and prints a ready-to-paste WORKDAY_COMPANIES entry, then does
a live 1-result test call so you can confirm the endpoint actually responds.
"""
from __future__ import annotations

import sys

import requests

from .workday_tenant import parse_workday_url


def parse(url: str) -> dict | None:
    return parse_workday_url(url)


def test_endpoint(info: dict) -> None:
    endpoint = (
        f"https://{info['tenant']}.{info['dc']}.myworkdayjobs.com"
        f"/wday/cxs/{info['tenant']}/{info['site']}/jobs"
    )
    print(f"\nTesting endpoint:\n  {endpoint}")
    try:
        resp = requests.post(
            endpoint,
            json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""},
            headers={"Accept": "application/json", "Content-Type": "application/json",
                     "User-Agent": "job-application-assistant/0.1"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        total = data.get("total", "?")
        sample = (data.get("jobPostings") or [{}])[0].get("title", "(no postings)")
        print(f"  OK — endpoint live. total jobs reported: {total}")
        print(f"  sample posting title: {sample}")
    except (requests.RequestException, ValueError) as exc:
        print(f"  FAILED — {exc}")
        print("  (Double-check the site slug; some companies use a different path "
              "segment or data center.)")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    info = parse(sys.argv[1])
    if not info:
        print("Could not parse that URL. Expected something like:")
        print("  https://COMPANY.wdN.myworkdayjobs.com/SiteSlug")
        sys.exit(1)

    name = info["tenant"].capitalize()
    print("Add this to WORKDAY_COMPANIES in finder/config.py:\n")
    print(f'    {{"name": "{name}", "tenant": "{info["tenant"]}", '
          f'"dc": "{info["dc"]}", "site": "{info["site"]}"}},')
    test_endpoint(info)


if __name__ == "__main__":
    main()
