"""Entry point: find jobs, optionally score them with the local model, and write
them to the chosen sink.

    python -m finder.run                       # find -> CSV (default)
    python -m finder.run --sink sheets         # find -> Google Sheet
    python -m finder.run --keywords imaging ml # override keywords
    python -m finder.run --expand              # model-expand keywords (you prune)
    python -m finder.run --score               # rank jobs by ring-aware fit (Phase 2)

What it does:
  1. Runs each configured source (Workday/Greenhouse/Lever/Arbeitnow).
  2. Annotates each job with location/role preferences (DESIGN.md §5).
  3. Optionally expands keywords and/or scores jobs with the local model (§6.5-6.7).
  4. Writes to the sink, deduping on job_key so re-runs only add new jobs.
"""
from __future__ import annotations

import argparse
import json
import os

from . import config
from .discovery import all_workday_companies, load_discovered
from .preferences import annotate
from .sinks import get_sink
from .sources import adzuna, arbeitnow, greenhouse, lever, workday


def gather(keywords: list[str]) -> list:
    jobs = []
    delay = config.REQUEST_DELAY_SECONDS

    # --- Free discovery feeds first: they auto-register Workday companies ---
    if config.ENABLE_ARBEITNOW:
        jobs += arbeitnow.fetch(keywords, delay=delay)
    # Adzuna only runs if a key is set (otherwise it prints a skip notice).
    jobs += adzuna.fetch(keywords, delay=delay)

    # --- Per-company ATS sources (all free, no key) ---
    companies = all_workday_companies(config.WORKDAY_COMPANIES)
    jobs += workday.fetch(keywords, companies, delay=delay)
    jobs += greenhouse.fetch(keywords, config.GREENHOUSE_COMPANIES, delay=delay)
    jobs += lever.fetch(keywords, config.LEVER_COMPANIES, delay=delay)

    return [annotate(j) for j in jobs]


def load_profile(path: str = None) -> dict:
    """Load your profile. Prefers profile.json (gitignored, your real data);
    falls back to profile.example.json so a fresh clone still runs."""
    here = os.path.dirname(__file__)
    if path is None:
        real = os.path.join(here, "profile.json")
        path = real if os.path.exists(real) else os.path.join(here, "profile.example.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def maybe_expand(keywords: list[str], profile: dict, interactive: bool) -> list[str]:
    """Phase 2: model-driven keyword expansion with a prune step."""
    from .expand import expand_keywords, prune_interactively
    from .llm import get_client
    from .llm.base import ModelError
    from .scorer import _profile_brief

    client = get_client(config)
    if not client.available():
        print("  [expand] local model not reachable — using your keywords as-is.")
        return keywords
    try:
        terms = expand_keywords(keywords, _profile_brief(profile), client)
    except ModelError as exc:
        print(f"  [expand] model error ({exc}); using your keywords as-is.")
        return keywords
    return prune_interactively(terms) if interactive else terms


def maybe_score(jobs: list, profile: dict) -> list:
    """Phase 2: ring-aware fit scoring; returns jobs sorted by rank desc."""
    from .llm import get_client
    from .scorer import score_jobs

    client = get_client(config)
    if not client.available():
        print("  [score] local model not reachable — skipping scoring. "
              "Install Ollama + `ollama pull qwen3:8b`, or set LLM_BACKEND='fake'.")
        return jobs
    print(f"  [score] scoring {len(jobs)} jobs with {getattr(config,'OLLAMA_MODEL','model')} …")
    scored = score_jobs(jobs, profile, client, on_error=config.LLM_ON_ERROR)
    ordered = []
    for job, result in scored:
        ordered.append(job.apply_score(result))
    # Any job the model skipped keeps its place at the end, unscored.
    scored_keys = {j.job_key for j in ordered}
    ordered += [j for j in jobs if j.job_key not in scored_keys]
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description="Find + score jobs into a sheet/CSV.")
    parser.add_argument("--sink", choices=["csv", "sheets"], default=config.DEFAULT_SINK)
    parser.add_argument("--keywords", nargs="*", default=None,
                        help="override config KEYWORDS for this run")
    parser.add_argument("--expand", action="store_true",
                        help="model-expand keywords before searching (you prune)")
    parser.add_argument("--score", action="store_true",
                        help="score + rank jobs with the local model (Phase 2)")
    parser.add_argument("--no-prune", action="store_true",
                        help="with --expand, skip the interactive prune step")
    args = parser.parse_args()

    profile = load_profile()
    keywords = args.keywords if args.keywords else config.KEYWORDS

    if args.expand:
        keywords = maybe_expand(keywords, profile, interactive=not args.no_prune)
    print(f"Searching keywords: {', '.join(keywords)}")
    print(f"Workday companies: {len(config.WORKDAY_COMPANIES)} seeded + "
          f"{len(load_discovered())} auto-discovered")

    jobs = gather(keywords)
    kept = [j for j in jobs if j.status != "location_filtered"]
    filtered = len(jobs) - len(kept)
    print(f"\nGathered {len(jobs)} jobs ({filtered} outside your location rules, kept but tagged).")

    if args.score:
        jobs = maybe_score(jobs, profile)
        top = [j for j in jobs if j.ring in ("1", "2")][:5]
        if top:
            print("\nTop medicine-first matches:")
            for j in top:
                print(f"  [ring {j.ring} | rank {j.rank}] {j.title} @ {j.company}")

    added, skipped = get_sink(args.sink)(jobs)
    where = config.CSV_PATH if args.sink == "csv" else f"Google Sheet ({config.GOOGLE_WORKSHEET})"
    print(f"\nWrote to {where}: {added} new, {skipped} already present.")
    if args.sink == "csv" and added:
        print(f"Open {config.CSV_PATH} to see them (sorted by fit when --score is used).")


if __name__ == "__main__":
    main()
