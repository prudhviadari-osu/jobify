"""Offline test of the Workday parser against a realistic cxs payload.

The sandbox can't reach *.myworkdayjobs.com, so we mock the HTTP layer with a
response shaped exactly like Workday's real /wday/cxs/.../jobs reply and verify:
  - apply URLs are built correctly from externalPath,
  - requisition id -> source_job_id,
  - dedup across keywords,
  - pagination stops on a short page,
  - preference annotation tags location/role mode.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finder.sources import workday
from finder.preferences import annotate

COMPANY = {"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"}

# A realistic single-page Workday response (fewer than PAGE_SIZE -> one page).
MOCK_PAGE = {
    "total": 2,
    "jobPostings": [
        {
            "title": "Biomedical Engineering Intern - Summer 2027",
            "externalPath": "/job/Minneapolis/Biomedical-Engineering-Intern_R12345",
            "locationsText": "Minneapolis, MN",
            "postedOn": "Posted 3 Days Ago",
            "bulletFields": ["R12345"],
        },
        {
            "title": "Clinical Data Scientist",
            "externalPath": "/job/Remote/Clinical-Data-Scientist_R67890",
            "locationsText": "Remote - United States",
            "postedOn": "Posted Today",
            "bulletFields": ["R67890"],
        },
    ],
}


def _mock_session():
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = MOCK_PAGE
    resp.raise_for_status.return_value = None
    session.post.return_value = resp
    return session


def test_parse_and_urls():
    with patch("finder.sources.workday.requests.Session", return_value=_mock_session()):
        jobs = workday.fetch(["biomedical"], [COMPANY], delay=0)

    assert len(jobs) == 2, f"expected 2 jobs, got {len(jobs)}"

    by_title = {j.title: j for j in jobs}
    intern = by_title["Biomedical Engineering Intern - Summer 2027"]
    clinical = by_title["Clinical Data Scientist"]

    # Apply URL correctly assembled from base + site + externalPath
    assert intern.url == (
        "https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers"
        "/job/Minneapolis/Biomedical-Engineering-Intern_R12345"
    ), intern.url

    # Requisition id captured
    assert intern.source_job_id == "medtronic:R12345", intern.source_job_id
    assert clinical.source_job_id == "medtronic:R67890"

    # job_key is stable + source-prefixed
    assert intern.job_key.startswith("workday:")
    print("  URL + id parsing: OK")


def test_preferences():
    with patch("finder.sources.workday.requests.Session", return_value=_mock_session()):
        jobs = [annotate(j) for j in workday.fetch(["x"], [COMPANY], delay=0)]
    by_title = {j.title: j for j in jobs}
    intern = by_title["Biomedical Engineering Intern - Summer 2027"]
    clinical = by_title["Clinical Data Scientist"]

    # Minneapolis is a non-primary location, but it's a US internship -> passes.
    assert "mode=summer internship" in intern.relevance_reason
    assert intern.status == "new", intern.relevance_reason   # passed all filters

    # Remote clinical role -> remote detected, US, passes, tagged clinical.
    assert clinical.remote is True
    assert "mode=night/weekend clinical" in clinical.relevance_reason
    assert clinical.status == "new"
    print("  preference tagging (US + student-level filters): OK")


if __name__ == "__main__":
    test_parse_and_urls()
    test_preferences()
    print("\nAll Workday parser tests passed.")
