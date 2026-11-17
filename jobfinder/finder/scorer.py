"""Phase 2: ring-aware fit-finder (DESIGN.md §6.6 / §6.7).

For each job, ask the model to assign:
  - ring (1 core medicine / 2 medical-AI-medtech / 3 adjacent tech / 4 off-path)
  - fit_score  (can the candidate do it)      0..1
  - path_score (does it serve a pre-med path) 0..1
plus advisor fields (verdict, positioning, gaps, next action).

Ranking = fit * path, so a medical-AI role with medium fit outranks a perfect
non-medical ML job. Every ring-3 job is labeled off-path.
"""
from __future__ import annotations

import json

from .llm.base import ModelClient, ModelError
from .models import NormalizedJob

SYSTEM = """You are a career advisor for a pre-med Computer Science student.
His PATH is medicine (he wants to be a doctor); technical roles are welcome only
when they serve that path. Rank by both: can he do the job, AND does it advance a
pre-med headed toward medicine (with ML as a tool).

Assign a priority RING:
  1 = core medicine / clinical (clinical hours, patient exposure, research assistant)
  2 = medical AI / medtech / biomedical (medical imaging AI, clinical data, devices) -- EQUAL top priority to 1
  3 = adjacent technical, NO medical angle (general ML/data/software) -- allowed but off-path
  4 = off-path non-technical (unrelated) -- lowest

Rules:
- Base every judgment ONLY on the candidate profile and the job text provided.
- Do NOT invent skills or experience he does not have.
- For ring 3 and 4, set off_path_note explaining it gives no clinical/medical value.
Return ONLY JSON with keys: ring (int 1-4), fit_score (0-1), path_score (0-1),
fit_verdict (str), positioning_advice (str), gaps (str), next_action (str),
off_path_note (str)."""


def _profile_brief(profile: dict) -> str:
    """A compact profile string for the prompt (keeps tokens low)."""
    basics = profile.get("basics", {})
    exp = "; ".join(
        f"{e.get('title','')} @ {e.get('company','')}" for e in profile.get("experience", [])
    )
    skills = profile.get("skills", {})
    skill_flat = []
    if isinstance(skills, dict):
        for v in skills.values():
            skill_flat += v if isinstance(v, list) else [v]
    elif isinstance(skills, list):
        skill_flat = skills
    edu = "; ".join(f"{e.get('degree','')} {e.get('field','')}" for e in profile.get("education", []))
    return (
        f"Pre-med CS student. Education: {edu}. "
        f"Experience: {exp}. Skills: {', '.join(skill_flat)}. "
        f"Summary: {profile.get('summary','')}"
    )


def score_job(job: NormalizedJob, profile_brief: str, client: ModelClient) -> dict:
    user = (
        f"CANDIDATE PROFILE:\n{profile_brief}\n\n"
        f"JOB:\nTitle: {job.title}\nCompany: {job.company}\n"
        f"Location: {job.location}\nDescription: {job.description[:1500]}\n\n"
        "Score this job as instructed. JSON only."
    )
    result = client.generate_json(SYSTEM, user, temperature=0.2)
    if not isinstance(result, dict):
        raise ModelError("scorer expected a JSON object")
    return _sanitize(result)


def _sanitize(r: dict) -> dict:
    """Clamp/normalize model output so downstream code is safe."""
    def num(x, default):
        try:
            return max(0.0, min(1.0, float(x)))
        except (TypeError, ValueError):
            return default
    ring = r.get("ring", 3)
    try:
        ring = int(ring)
    except (TypeError, ValueError):
        ring = 3
    ring = ring if ring in (1, 2, 3, 4) else 3
    fit = num(r.get("fit_score"), 0.5)
    path = num(r.get("path_score"), 0.5)
    return {
        "ring": ring,
        "fit_score": fit,
        "path_score": path,
        "rank": round(fit * path, 4),
        "fit_verdict": str(r.get("fit_verdict", "")),
        "positioning_advice": str(r.get("positioning_advice", "")),
        "gaps": str(r.get("gaps", "")),
        "next_action": str(r.get("next_action", "review")),
        "off_path_note": str(r.get("off_path_note", "")) if ring >= 3 else "",
    }


def score_jobs(jobs: list[NormalizedJob], profile: dict, client: ModelClient,
               on_error: str = "skip") -> list[tuple[NormalizedJob, dict]]:
    """Score a list; returns (job, result) sorted by rank desc.
    on_error='skip' drops jobs the model choked on (logged); 'raise' re-raises."""
    brief = _profile_brief(profile)
    scored = []
    for job in jobs:
        try:
            scored.append((job, score_job(job, brief, client)))
        except ModelError as exc:
            if on_error == "raise":
                raise
            print(f"    [scorer] skipped '{job.title}' — {exc}")
    scored.sort(key=lambda t: (t[1]["rank"], -t[1]["ring"]), reverse=True)
    return scored
