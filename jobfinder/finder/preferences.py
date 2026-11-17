"""Apply the location/role preference rules from DESIGN.md §5.

Rules:
  - Columbus / Remote / Ohio are always acceptable.
  - Other locations are acceptable ONLY for summer-internship-type roles.
  - Night/weekend clinical roles are acceptable year-round (still location-gated
    to primary locations unless they're also internships).
A job that fails the location rule is kept but tagged, so nothing is silently
dropped — you can still see everything in the sheet and decide.
"""
from __future__ import annotations

from . import config
from .models import NormalizedJob


def _text(job: NormalizedJob) -> str:
    return f"{job.title} {job.location}".lower()


def is_internship(job: NormalizedJob) -> bool:
    t = job.title.lower()
    return any(h in t for h in config.INTERNSHIP_HINTS)


def is_clinical(job: NormalizedJob) -> bool:
    t = job.title.lower()
    return any(h in t for h in config.CLINICAL_HINTS)


def location_ok(job: NormalizedJob) -> bool:
    loc = job.location.lower()
    if not loc:
        return True  # unknown location — don't drop, let the human judge
    if any(p in loc for p in config.LOCATIONS_PRIMARY):
        return True
    if job.remote:
        return True
    # Other locations: only for summer internships.
    if config.ALLOW_OTHER_LOCATIONS_FOR_INTERNSHIPS and is_internship(job):
        return True
    return False


def role_mode(job: NormalizedJob) -> str:
    if is_internship(job):
        return "summer internship"
    if is_clinical(job):
        return "night/weekend clinical"
    return "other"


def annotate(job: NormalizedJob) -> NormalizedJob:
    """Mark remote + a preference note in relevance_reason (Phase 1 placeholder
    until the model scores in Phase 2)."""
    if "remote" in _text(job):
        job.remote = True
    ok = location_ok(job)
    mode = role_mode(job)
    job.relevance_reason = f"mode={mode}; location_ok={ok}"
    if not ok:
        job.status = "location_filtered"
    return job
