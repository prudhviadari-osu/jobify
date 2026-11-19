"""Apply location/role/level preference rules (DESIGN.md §5, extended).

Rules:
  - US-only: drop jobs clearly outside the United States (config.US_ONLY).
  - Student-level: keep internships / entry / new-grad; drop senior roles
    (config.STUDENT_LEVEL_ONLY).
  - Location: Columbus / Remote / Ohio always OK; other US locations OK only for
    internships (the existing summer rule).
  - Night/weekend clinical roles stay flagged.

Filtered jobs are not silently deleted — they get status set to why they were
dropped (location_filtered / non_us / not_student_level) and a reason, so you can
still inspect them if you widen the filters.
"""
from __future__ import annotations

from . import config
from .models import NormalizedJob


def _title(job: NormalizedJob) -> str:
    return (job.title or "").lower()


def _loc(job: NormalizedJob) -> str:
    return (job.location or "").lower()


def is_internship(job: NormalizedJob) -> bool:
    t = _title(job)
    return any(h in t for h in config.INTERNSHIP_HINTS)


def is_clinical(job: NormalizedJob) -> bool:
    t = _title(job)
    return any(h in t for h in config.CLINICAL_HINTS)


# --- US-only ---
def is_us(job: NormalizedJob) -> bool:
    loc = _loc(job)
    if not loc:
        return True   # unknown location — don't drop, let the human judge
    if job.remote:
        return True
    # Explicit non-US signal with no US signal -> not US.
    has_non_us = any(h in loc for h in config.NON_US_HINTS)
    has_us = any(h in loc for h in config.US_LOCATION_HINTS)
    if has_us:
        return True
    # State-code match, e.g. "Minneapolis, MN" or "Austin, TX".
    tokens = [t.strip(" ,()-") for t in loc.replace("/", " ").split()]
    if any(tok in config.US_STATE_CODES for tok in tokens):
        return True
    return not has_non_us  # if it names a foreign country, drop; otherwise keep


# --- Student / early-career level ---
def is_student_level(job: NormalizedJob) -> bool:
    t = _title(job)
    # Senior signals win: if it looks senior, it's not student-level.
    if any(h in t for h in config.SENIOR_LEVEL_HINTS):
        return False
    # Otherwise keep if it has a student/entry signal, OR if the title is level-
    # neutral (no seniority marker at all) — many entry roles don't say "junior".
    return True


def location_ok(job: NormalizedJob) -> bool:
    loc = _loc(job)
    if not loc:
        return True
    if any(p in loc for p in config.LOCATIONS_PRIMARY):
        return True
    if job.remote:
        return True
    # Any US location is fine for a student-level role (internships + new-grad +
    # entry). Since US-only + student-level filters already ran, reaching here means
    # it's a US student-level job — accept it regardless of city.
    if config.ALLOW_OTHER_LOCATIONS_FOR_INTERNSHIPS and (is_internship(job) or is_student_level(job)):
        return True
    return False


def role_mode(job: NormalizedJob) -> str:
    if is_internship(job):
        return "summer internship"
    if is_clinical(job):
        return "night/weekend clinical"
    return "other"


def annotate(job: NormalizedJob) -> NormalizedJob:
    """Apply filters in priority order. The FIRST failing filter sets the status
    and reason; a job that passes all is status='new'."""
    if "remote" in f"{_title(job)} {_loc(job)}":
        job.remote = True

    mode = role_mode(job)

    # 1. US-only (hard filter).
    if config.US_ONLY and not is_us(job):
        job.status = "non_us"
        job.relevance_reason = f"dropped: outside US ({job.location})"
        return job

    # 2. Student / early-career level (hard filter).
    if config.STUDENT_LEVEL_ONLY and not is_student_level(job):
        job.status = "not_student_level"
        job.relevance_reason = f"dropped: senior-level role (title: {job.title})"
        return job

    # 3. Location preference (soft — only blocks non-primary non-internships).
    if not location_ok(job):
        job.status = "location_filtered"
        job.relevance_reason = f"mode={mode}; location outside your rules ({job.location})"
        return job

    job.status = "new"
    job.relevance_reason = f"mode={mode}; US + student-level + location OK"
    return job
