"""Registry of Workday companies discovered automatically from Adzuna results.

When Adzuna returns a job whose apply URL is a Workday URL, we parse out the
company's tenant/dc/site and save it here. On the next run, the Workday source
polls these companies' full boards directly — so you don't hand-list companies;
searching discovers them.

Stored as a small JSON file next to the config so you can inspect/edit it.
"""
from __future__ import annotations

import json
import os

from . import config
from .workday_tenant import parse_workday_url, is_workday_url

DEFAULT_PATH = "discovered_companies.json"


def _path(path: str | None) -> str:
    """Resolve the registry path: explicit arg > config override > default.
    Reading it at call time (not as a frozen default) keeps it testable and
    lets users point it elsewhere via config."""
    if path:
        return path
    return getattr(config, "DISCOVERED_COMPANIES_PATH", "") or DEFAULT_PATH


def _key(company: dict) -> str:
    return f"{company['tenant']}/{company['dc']}/{company['site']}"


def load_discovered(path: str | None = None) -> list[dict]:
    path = _path(path)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return []


def save_discovered(companies: list[dict], path: str | None = None) -> None:
    with open(_path(path), "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2)


def register_from_url(url: str, path: str | None = None) -> dict | None:
    """If `url` is a parseable Workday URL, add its company to the registry.
    Returns the company dict if newly added, else None."""
    if not is_workday_url(url):
        return None
    company = parse_workday_url(url)
    if not company:
        return None

    existing = load_discovered(path)
    keys = {_key(c) for c in existing}
    if _key(company) in keys:
        return None
    existing.append(company)
    save_discovered(existing, path)
    return company


def all_workday_companies(seed: list[dict], path: str | None = None) -> list[dict]:
    """Seed companies (config) + discovered companies, deduped by tenant/dc/site."""
    merged: dict[str, dict] = {}
    for c in list(seed) + load_discovered(path):
        merged[_key(c)] = c
    return list(merged.values())
