"""Offline test of the Adzuna source + Workday auto-discovery.

Sandbox can't reach api.adzuna.com, so we mock the HTTP layer with a response
shaped like Adzuna's real `results` payload — including one job whose
redirect_url is a Workday apply URL — and verify:
  - jobs are parsed into NormalizedJob,
  - the Workday company is auto-discovered and written to the registry,
  - merging seed + discovered companies dedupes correctly.
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finder import config, discovery
from finder.sources import adzuna
from finder.workday_tenant import parse_workday_url

MOCK_RESULTS = {
    "results": [
        {
            "id": "111",
            "title": "Biomedical Data Scientist",
            "company": {"display_name": "Medtronic"},
            "location": {"display_name": "Remote, US"},
            # A real Workday apply URL -> should be auto-discovered
            "redirect_url": "https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers/job/Remote/Data-Scientist_R999",
            "description": "Work on medical imaging ML.",
            "created": "2026-11-10T00:00:00Z",
        },
        {
            "id": "222",
            "title": "Clinical Research Coordinator",
            "company": {"display_name": "SomeHospital"},
            "location": {"display_name": "Columbus, OH"},
            "redirect_url": "https://example.com/apply/222",   # not Workday
            "description": "Coordinate clinical trials.",
            "created": "2026-11-11T00:00:00Z",
        },
    ]
}


def _mock_session(payload):
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    session.get.return_value = resp
    return session


def test_parse_workday_url_variants():
    # with language segment + job path
    info = parse_workday_url(
        "https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers/job/Remote/X_R1"
    )
    assert info == {"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"}, info
    # bare careers url, no language segment
    info2 = parse_workday_url("https://iqvia.wd1.myworkdayjobs.com/IQVIA")
    assert info2["tenant"] == "iqvia" and info2["site"] == "IQVIA"
    print("  URL parsing (variants): OK")


def test_adzuna_fetch_and_discovery():
    with tempfile.TemporaryDirectory() as d:
        reg = os.path.join(d, "discovered.json")
        # Point the registry at a temp file via config, mock key + HTTP session.
        with patch.object(config, "DISCOVERED_COMPANIES_PATH", reg), \
             patch.object(config, "ADZUNA_APP_ID", "x"), \
             patch.object(config, "ADZUNA_APP_KEY", "y"), \
             patch("finder.sources.adzuna.requests.Session",
                   return_value=_mock_session(MOCK_RESULTS)), \
             patch("finder.sources.adzuna.MAX_PAGES", 1):
            jobs = adzuna.fetch(["biomedical"], delay=0)

        assert len(jobs) == 2, f"expected 2 jobs, got {len(jobs)}"
        titles = {j.title for j in jobs}
        assert "Biomedical Data Scientist" in titles
        assert "Clinical Research Coordinator" in titles

        # The Workday company should have been registered.
        found = discovery.load_discovered(reg)
        assert len(found) == 1, f"expected 1 discovered company, got {found}"
        assert found[0]["tenant"] == "medtronic", found
        print("  Adzuna parse + Workday auto-discovery: OK")


def test_merge_dedup():
    with tempfile.TemporaryDirectory() as d:
        reg = os.path.join(d, "discovered.json")
        discovery.save_discovered(
            [{"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"}],
            reg,
        )
        seed = [{"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"},
                {"name": "IQVIA", "tenant": "iqvia", "dc": "wd1", "site": "IQVIA"}]
        merged = discovery.all_workday_companies(seed, reg)
        # Medtronic appears in both -> deduped to one; IQVIA unique -> 2 total.
        assert len(merged) == 2, f"expected 2 after dedup, got {len(merged)}"
        print("  seed + discovered merge/dedup: OK")


if __name__ == "__main__":
    test_parse_workday_url_variants()
    test_adzuna_fetch_and_discovery()
    test_merge_dedup()
    print("\nAll Adzuna + discovery tests passed.")
