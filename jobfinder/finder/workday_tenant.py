"""Parse a myworkdayjobs.com URL into its tenant/dc/site parts.

Shared by resolve_workday.py (manual) and the Adzuna source (auto-discovery).
A Workday careers/apply URL looks like:

    https://{tenant}.{dc}.myworkdayjobs.com[/{lang}]/{site}[/job/...]

e.g. https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers/job/...
"""
from __future__ import annotations

import re

# tenant.dc.myworkdayjobs.com / [optional lang segment] / site / [rest]
_PATTERN = re.compile(
    r"https?://(?P<tenant>[^./]+)\.(?P<dc>wd\d+)\.myworkdayjobs\.com/"
    r"(?:(?P<lang>[a-z]{2}-[A-Z]{2})/)?"
    r"(?P<site>[^/?#]+)"
)


def is_workday_url(url: str) -> bool:
    return "myworkdayjobs.com" in (url or "")


def parse_workday_url(url: str) -> dict | None:
    """Return {name, tenant, dc, site} or None if the URL isn't a parseable
    Workday careers/apply URL."""
    if not url:
        return None
    m = _PATTERN.search(url.strip())
    if not m:
        return None
    tenant = m.group("tenant")
    return {
        "name": tenant.capitalize(),
        "tenant": tenant,
        "dc": m.group("dc"),
        "site": m.group("site"),
    }
