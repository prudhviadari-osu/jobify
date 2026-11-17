"""Offline tests for the Greenhouse and Lever sources: parsing, HTML stripping,
keyword filtering, Lever pagination, and remote detection. HTTP is mocked
(sandbox can't reach the live APIs)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finder.sources import greenhouse, lever

# ---- Greenhouse ----
GH_PAYLOAD = {
    "jobs": [
        {
            "id": 101,
            "title": "Machine Learning Engineer, Medical Imaging",
            "location": {"name": "Remote - US"},
            "absolute_url": "https://boards.greenhouse.io/tempus/jobs/101",
            "updated_at": "2026-11-10T00:00:00Z",
            "content": "&lt;p&gt;Build &lt;b&gt;medical imaging&lt;/b&gt; models.&lt;/p&gt;",
        },
        {
            "id": 102,
            "title": "Office Manager",            # should be filtered out
            "location": {"name": "Chicago, IL"},
            "absolute_url": "https://boards.greenhouse.io/tempus/jobs/102",
            "updated_at": "2026-11-09T00:00:00Z",
            "content": "&lt;p&gt;Manage the office.&lt;/p&gt;",
        },
    ]
}


def _mock_get(payload):
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    session.get.return_value = resp
    return session


def test_greenhouse():
    with patch("finder.sources.greenhouse.requests.Session", return_value=_mock_get(GH_PAYLOAD)):
        jobs = greenhouse.fetch(["imaging", "machine learning"],
                                [{"name": "Tempus", "slug": "tempus", "ring": 2}], delay=0)
    assert len(jobs) == 1, f"expected 1 match, got {len(jobs)}"
    j = jobs[0]
    assert j.source == "greenhouse"
    assert j.company == "Tempus"
    assert j.source_job_id == "tempus:101"
    assert j.url == "https://boards.greenhouse.io/tempus/jobs/101"
    # HTML entities unescaped and tags stripped
    assert "<" not in j.description and "medical imaging" in j.description, j.description
    print("  greenhouse parse + HTML strip + filter: OK")


# ---- Lever (two pages, second short -> stop) ----
LEVER_PAGE_1 = [
    {
        "id": "abc",
        "text": "Clinical Data Scientist",
        "hostedUrl": "https://jobs.lever.co/examplebio/abc",
        "applyUrl": "https://jobs.lever.co/examplebio/abc/apply",
        "categories": {"location": "Boston, MA", "team": "Data"},
        "workplaceType": "remote",
        "descriptionPlain": "Analyze clinical trial data.",
        "createdAt": 1730000000000,
    },
    {
        "id": "def",
        "text": "Barista",                        # filtered out
        "hostedUrl": "https://jobs.lever.co/examplebio/def",
        "categories": {"location": "NYC"},
        "workplaceType": "on-site",
        "descriptionPlain": "Make coffee.",
        "createdAt": 1730000001000,
    },
]


def _mock_paged(pages):
    session = MagicMock()
    responses = []
    for p in pages:
        r = MagicMock()
        r.json.return_value = p
        r.raise_for_status.return_value = None
        responses.append(r)
    session.get.side_effect = responses
    return session


def test_lever():
    # page 1 has 2 rows (< PAGE_SIZE 50) so it stops after one page
    with patch("finder.sources.lever.requests.Session",
               return_value=_mock_paged([LEVER_PAGE_1])):
        jobs = lever.fetch(["clinical", "data"],
                           [{"name": "ExampleBio", "slug": "examplebio", "ring": 2}], delay=0)
    assert len(jobs) == 1, f"expected 1 match, got {len(jobs)}"
    j = jobs[0]
    assert j.source == "lever"
    assert j.source_job_id == "examplebio:abc"
    assert j.remote is True
    assert j.location == "Boston, MA"
    assert j.url == "https://jobs.lever.co/examplebio/abc"
    print("  lever parse + pagination stop + remote + filter: OK")


if __name__ == "__main__":
    test_greenhouse()
    test_lever()
    print("\nGreenhouse + Lever tests passed.")
