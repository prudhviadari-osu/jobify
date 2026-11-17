"""The single normalized job shape every source produces.

This mirrors the `Jobs` tab schema in DESIGN.md §4. Every source plugin returns
a list of NormalizedJob, so the rest of the pipeline never cares which source a
job came from.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone


# Column order used for CSV and the Google Sheet `Jobs` tab.
FIELDNAMES = [
    "job_key",
    "source",
    "company",
    "title",
    "location",
    "remote",
    "url",
    "description",
    "posted_at",
    "found_at",
    "status",
    "relevance_score",
    "relevance_reason",
]


@dataclass
class NormalizedJob:
    source: str                 # 'workday' | 'adzuna' | 'greenhouse' | 'lever'
    source_job_id: str          # id within that source (requisition id, etc.)
    company: str
    title: str
    location: str = ""
    remote: bool = False
    url: str = ""
    description: str = ""
    posted_at: str = ""
    found_at: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    status: str = "new"
    relevance_score: str = ""   # filled in Phase 2
    relevance_reason: str = ""  # filled in Phase 2

    @property
    def job_key(self) -> str:
        """Stable dedup key. Combines source + source id; hashed so it is safe
        as a spreadsheet cell and consistent across runs."""
        raw = f"{self.source}:{self.source_job_id}"
        # Keep it human-readable but bounded.
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
        return f"{self.source}:{digest}"

    def to_row(self) -> dict:
        d = asdict(self)
        d.pop("source_job_id", None)
        d["job_key"] = self.job_key
        d["remote"] = "yes" if self.remote else "no"
        # Keep description bounded so the sheet/CSV stays readable.
        if d["description"] and len(d["description"]) > 1500:
            d["description"] = d["description"][:1500] + " …[truncated]"
        return {k: d.get(k, "") for k in FIELDNAMES}
