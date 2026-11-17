"""Profile-driven keyword expansion (DESIGN.md §6.5 / §6.7).

Given your seed keywords + profile, the model proposes related search terms
across the priority rings (medicine + medical-AI heavy, general tech as a
secondary layer). You prune the list before it's used — the model proposes,
you approve.
"""
from __future__ import annotations

from .llm.base import ModelClient, ModelError

SYSTEM = """You expand a pre-med CS student's job-search keywords. His path is
medicine; technical skills (ML, data) are tools that serve it. Given seed terms
and his profile, propose related SEARCH keywords, weighted toward:
  - core medicine / clinical roles, and
  - medical AI / medtech / biomedical roles,
with a smaller number of adjacent general-technical terms (ML/data/software).
Keep terms short and realistic as job-search queries. Do not invent skills.
Return ONLY JSON: {"keywords": ["term", ...]} with at most 20 terms."""


def expand_keywords(seeds: list[str], profile_brief: str, client: ModelClient) -> list[str]:
    user = (
        f"SEED KEYWORDS: {', '.join(seeds)}\n"
        f"PROFILE: {profile_brief}\n\n"
        "Propose the expanded keyword list. JSON only."
    )
    result = client.generate_json(SYSTEM, user, temperature=0.4)
    terms = result.get("keywords", []) if isinstance(result, dict) else result
    if not isinstance(terms, list):
        raise ModelError("expansion expected a list of keywords")
    # De-dupe (case-insensitive), preserve order, keep seeds first.
    out, seen = [], set()
    for t in list(seeds) + [str(x) for x in terms]:
        key = t.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(t.strip())
    return out[:30]


def prune_interactively(terms: list[str]) -> list[str]:
    """Show the proposed terms and let the user drop any (CLI prompt).
    Non-interactive callers can skip this and use the list as-is."""
    print("\nProposed search keywords (model-expanded):")
    for i, t in enumerate(terms, 1):
        print(f"  {i:2}. {t}")
    raw = input("\nEnter numbers to REMOVE (comma-separated), or Enter to keep all: ").strip()
    if not raw:
        return terms
    drop = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            drop.add(int(part))
    kept = [t for i, t in enumerate(terms, 1) if i not in drop]
    print(f"Keeping {len(kept)} terms.")
    return kept
