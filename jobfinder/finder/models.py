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
    # --- Phase 2: ring-aware fit-finder fields (blank until scored) ---
    "ring",
    "fit_score",
    "path_score",
    "rank",
    "fit_verdict",
    "positioning_advice",
    "gaps",
    "next_action",
    "off_path_note",
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
    relevance_score: str = ""
    relevance_reason: str = ""
    # --- Phase 2: ring-aware fit-finder (blank until scored) ---
    ring: str = ""
    fit_score: str = ""
    path_score: str = ""
    rank: str = ""
    fit_verdict: str = ""
    positioning_advice: str = ""
    gaps: str = ""
    next_action: str = ""
    off_path_note: str = ""

    def apply_score(self, result: dict) -> "NormalizedJob":
        """Copy a scorer result (scorer._sanitize output) onto this job."""
        self.ring = str(result.get("ring", ""))
        self.fit_score = str(result.get("fit_score", ""))
        self.path_score = str(result.get("path_score", ""))
        self.rank = str(result.get("rank", ""))
        self.fit_verdict = str(result.get("fit_verdict", ""))
        self.positioning_advice = str(result.get("positioning_advice", ""))
        self.gaps = str(result.get("gaps", ""))
        self.next_action = str(result.get("next_action", ""))
        self.off_path_note = str(result.get("off_path_note", ""))
        self.status = "scored"
        return self

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
