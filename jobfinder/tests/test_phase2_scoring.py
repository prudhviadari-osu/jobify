"""Offline tests for Phase 2: JSON extraction, ring-aware scoring, ranking order,
sanitization, and keyword expansion — all using the deterministic FakeClient (no
Ollama needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finder.llm import FakeClient
from finder.llm.base import extract_json, ModelError
from finder.models import NormalizedJob
from finder.scorer import score_jobs, _sanitize, _profile_brief
from finder.expand import expand_keywords

PROFILE = {
    "basics": {}, "summary": "pre-med CS student, ML + biomedical research",
    "experience": [{"title": "Research Assistant", "company": "IBRC"}],
    "education": [{"degree": "BS", "field": "Computer Science"}],
    "skills": {"ml": ["XGBoost", "PyTorch"], "bio": ["DXA/CT imaging"]},
}


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('<think>hmm</think>\n{"a": 3}') == {"a": 3}
    assert extract_json('Here you go: {"a": 4} done') == {"a": 4}
    try:
        extract_json("no json here")
        assert False, "should have raised"
    except ModelError:
        pass
    print("  extract_json (fences/think/prose/failure): OK")


def test_sanitize_clamps():
    out = _sanitize({"ring": 9, "fit_score": 5, "path_score": -2})
    assert out["ring"] == 3                 # invalid ring -> default 3
    assert out["fit_score"] == 1.0          # clamped to 1
    assert out["path_score"] == 0.0         # clamped to 0
    assert out["rank"] == 0.0
    # ring>=3 keeps off_path_note; here default empty is fine
    print("  _sanitize clamps ring/score ranges: OK")


def test_ring_ranking_order():
    client = FakeClient()
    jobs = [
        NormalizedJob("x", "1", "FintechCo", "Machine Learning Engineer",
                      description="build ML models for payments, data science"),
        NormalizedJob("x", "2", "HospitalX", "Clinical Research Assistant",
                      description="support patient clinical research in hospital"),
        NormalizedJob("x", "3", "MedAICo", "Medical Imaging AI Scientist",
                      description="biomedical medical imaging diagnostic ML models"),
    ]
    scored = score_jobs(jobs, PROFILE, client)
    rings = [r["ring"] for _, r in scored]
    # Medicine (1) and medical-AI (2) should outrank the pure-ML fintech (3).
    assert rings[0] in (1, 2) and rings[1] in (1, 2), rings
    assert rings[-1] == 3, f"pure-ML job should rank last: {rings}"
    # The ring-3 job must carry the off-path note.
    ml_result = next(r for _, r in scored if r["ring"] == 3)
    assert "off-path" in ml_result["off_path_note"], ml_result
    print(f"  ring-aware ranking (order {rings}) + off-path label: OK")


def test_apply_score_to_job():
    client = FakeClient()
    job = NormalizedJob("x", "9", "MedAICo", "Clinical Data Scientist",
                        description="clinical data biomedical ML")
    scored = score_jobs([job], PROFILE, client)
    j = scored[0][0].apply_score(scored[0][1])
    row = j.to_row()
    assert row["ring"] in ("1", "2")
    assert row["status"] == "scored"
    assert row["rank"] != ""
    print("  apply_score populates row fields: OK")


def test_keyword_expansion():
    client = FakeClient()
    terms = expand_keywords(["biomedical"], _profile_brief(PROFILE), client)
    assert "biomedical" in [t.lower() for t in terms]   # seeds preserved first
    assert len(terms) <= 30
    assert len(terms) > 1                                 # model added some
    print(f"  keyword expansion ({len(terms)} terms, seeds preserved): OK")


if __name__ == "__main__":
    test_extract_json_variants()
    test_sanitize_clamps()
    test_ring_ranking_order()
    test_apply_score_to_job()
    test_keyword_expansion()
    print("\nAll Phase 2 scoring tests passed.")
