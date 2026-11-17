"""Deterministic offline model, for tests and for a no-model dry run.

It does NOT do real language understanding — it applies simple keyword rules that
mimic the SHAPE of what the real model returns, so the surrounding pipeline
(scoring, ranking, advisor output) can be exercised without Ollama. Use it by
setting LLM_BACKEND='fake'.
"""
from __future__ import annotations

from .base import ModelClient


# Signals that push a job toward each ring (rough, keyword-based).
_RING1 = ["clinical", "patient", "hospital", "medical scribe", "research assistant", "nursing"]
_RING2 = ["biomedical", "medical imaging", "medical device", "bioinformatics",
          "health", "clinical data", "radiolog", "genomic", "diagnostic"]
_RING3 = ["machine learning", "data scien", "software", "computer vision", "engineer", "ml "]


class FakeClient(ModelClient):
    def available(self) -> bool:
        return True

    def generate_json(self, system: str, user: str, temperature: float = 0.2):
        # Keyword-expansion prompt -> return a small term list.
        if "expand" in system.lower() or "keywords" in system.lower():
            return {"keywords": ["clinical research", "medical imaging",
                                 "biomedical", "machine learning", "data science"]}

        # Score prompt: only inspect the JOB portion, not the candidate profile
        # (the profile mentions clinical/research and would skew the keyword match).
        u = user.lower()
        if "job:" in u:
            u = u.split("job:", 1)[1]

        r1 = sum(k in u for k in _RING1)
        r2 = sum(k in u for k in _RING2)
        r3 = sum(k in u for k in _RING3)

        if r1 >= r2 and r1 > 0:
            ring, path = 1, 0.9
        elif r2 > 0:
            ring, path = 2, 0.9
        elif r3 > 0:
            ring, path = 3, 0.4
        else:
            ring, path = 4, 0.1

        fit = min(1.0, 0.4 + 0.15 * (r1 + r2 + r3))
        return {
            "ring": ring,
            "fit_score": round(fit, 2),
            "path_score": path,
            "fit_verdict": f"(fake) ring {ring}; matched signals r1={r1} r2={r2} r3={r3}",
            "positioning_advice": "(fake) emphasize ML + research experience",
            "gaps": "(fake) none detected by stub",
            "next_action": "apply" if ring <= 2 and fit >= 0.5 else "review",
            "off_path_note": "" if ring <= 2 else "off-path: no clinical hours or medical exposure",
        }
