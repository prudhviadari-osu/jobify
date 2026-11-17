"""Phase 1 entry point: find medtech jobs and write them to the chosen sink.

    python -m finder.run                      # CSV (default)
    python -m finder.run --sink sheets        # Google Sheet (needs setup)
    python -m finder.run --keywords imaging ml

What it does:
  1. Runs each configured source (Workday today; Adzuna/Greenhouse pluggable).
  2. Annotates each job with location/role preferences (DESIGN.md §5).
  3. Writes to the sink, deduping on job_key so re-runs only add new jobs.
"""
from __future__ import annotations

import argparse

from . import config
from .discovery import all_workday_companies, load_discovered
from .preferences import annotate
from .sinks import get_sink
from .sources import adzuna, workday


def gather(keywords: list[str]) -> list:
    jobs = []

    # --- Adzuna first: broad discovery + auto-registers Workday companies ---
    jobs += adzuna.fetch(keywords, delay=config.REQUEST_DELAY_SECONDS)

    # --- Workday: poll seed companies PLUS any discovered via Adzuna ---
    companies = all_workday_companies(config.WORKDAY_COMPANIES)
    jobs += workday.fetch(keywords, companies, delay=config.REQUEST_DELAY_SECONDS)

    # --- Greenhouse / Lever plug in here with the same shape when enabled ---

    return [annotate(j) for j in jobs]


def main() -> None:
    parser = argparse.ArgumentParser(description="Find medtech jobs into a sheet/CSV.")
    parser.add_argument("--sink", choices=["csv", "sheets"], default=config.DEFAULT_SINK)
    parser.add_argument("--keywords", nargs="*", default=None,
                        help="override config KEYWORDS for this run")
    args = parser.parse_args()

    keywords = args.keywords if args.keywords else config.KEYWORDS
    print(f"Searching keywords: {', '.join(keywords)}")
    seeded = len(config.WORKDAY_COMPANIES)
    discovered = len(load_discovered())
    print(f"Workday companies: {seeded} seeded + {discovered} auto-discovered")

    jobs = gather(keywords)
    kept = [j for j in jobs if j.status != "location_filtered"]
    filtered = len(jobs) - len(kept)
    print(f"\nGathered {len(jobs)} jobs ({filtered} outside your location rules, kept but tagged).")

    added, skipped = get_sink(args.sink)(jobs)
    where = config.CSV_PATH if args.sink == "csv" else f"Google Sheet ({config.GOOGLE_WORKSHEET})"
    print(f"Wrote to {where}: {added} new, {skipped} already present.")
    if args.sink == "csv" and added:
        print(f"Open {config.CSV_PATH} to see them.")


if __name__ == "__main__":
    main()
