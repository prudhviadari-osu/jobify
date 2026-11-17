"""Offline test of the Arbeitnow source: keyword filtering, parsing, pagination,
and Workday auto-discovery from a feed URL. Mocks the HTTP layer (sandbox can't
reach arbeitnow.com)."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finder import config, discovery
from finder.sources import arbeitnow

PAGE_1 = {
    "data": [
        {
            "slug": "a1",
            "title": "Biomedical Engineer",
            "company_name": "Medtronic",
            "location": "Remote",
            "remote": True,
            "url": "https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers/job/R1",
            "tags": ["engineering", "biomedical"],
            "description": "Work on medical imaging.",
            "created_at": 1730000000,
        },
        {
            "slug": "a2",
            "title": "Warehouse Associate",     # should NOT match medtech keywords
            "company_name": "LogisticsCo",
            "location": "Berlin",
            "remote": False,
            "url": "https://example.com/apply/a2",
            "tags": ["logistics"],
            "description": "Move boxes.",
            "created_at": 1730000001,
        },
    ],
    "links": {"next": "https://www.arbeitnow.com/api/job-board-api?page=2"},
}
PAGE_2 = {"data": [], "links": {"next": None}}


def _mock_session(pages):
    session = MagicMock()
    responses = []
    for p in pages:
        r = MagicMock()
        r.json.return_value = p
        r.raise_for_status.return_value = None
        responses.append(r)
    session.get.side_effect = responses
    return session


def test_filter_parse_discover():
    with tempfile.TemporaryDirectory() as d:
        reg = os.path.join(d, "discovered.json")
        with patch.object(config, "DISCOVERED_COMPANIES_PATH", reg), \
             patch("finder.sources.arbeitnow.requests.Session",
                   return_value=_mock_session([PAGE_1, PAGE_2])):
            jobs = arbeitnow.fetch(["biomedical", "imaging", "clinical"], delay=0)

        # Only the biomedical job matches; warehouse is filtered out.
        assert len(jobs) == 1, f"expected 1 matched job, got {len(jobs)}"
        assert jobs[0].company == "Medtronic"
        assert jobs[0].remote is True
        assert jobs[0].source == "arbeitnow"

        # Its Workday URL should have been auto-discovered.
        found = discovery.load_discovered(reg)
        assert len(found) == 1 and found[0]["tenant"] == "medtronic", found
        print("  arbeitnow filter + parse + Workday discovery: OK")


if __name__ == "__main__":
    test_filter_parse_discover()
    print("\nArbeitnow test passed.")
