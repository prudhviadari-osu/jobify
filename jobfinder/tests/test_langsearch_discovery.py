"""Offline test: LangSearch discovery extracts Workday company URLs from search
results and registers them. HTTP mocked (sandbox can't reach the API)."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finder import config, discovery
from finder.sources import langsearch_discovery

# A realistic LangSearch response: two Workday career URLs + one non-Workday result.
MOCK = {
    "code": "200",
    "data": {"webPages": {"value": [
        {"name": "Careers at Medtronic",
         "url": "https://medtronic.wd1.myworkdayjobs.com/en-US/MedtronicCareers"},
        {"name": "Stryker Jobs",
         "url": "https://stryker.wd1.myworkdayjobs.com/StrykerCareers/job/X_R1"},
        {"name": "Some blog about jobs", "url": "https://example.com/blog"},
    ]}},
}


def _mock_session(payload):
    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    session.post.return_value = resp
    return session


def test_discovery_registers_workday_companies():
    with tempfile.TemporaryDirectory() as d:
        reg = os.path.join(d, "discovered.json")
        with patch.object(config, "LANGSEARCH_API_KEY", "test-key"), \
             patch.object(config, "DISCOVERED_COMPANIES_PATH", reg), \
             patch("finder.sources.langsearch_discovery.requests.Session",
                   return_value=_mock_session(MOCK)), \
             patch.object(langsearch_discovery, "DISCOVERY_DOMAINS", ["myworkdayjobs.com"]):
            n = langsearch_discovery.discover(["biomedical"], delay=0)

        # Two Workday URLs found -> two companies registered; the blog is ignored.
        assert n == 2, f"expected 2 discovered, got {n}"
        found = {c["tenant"] for c in discovery.load_discovered(reg)}
        assert found == {"medtronic", "stryker"}, found
        print("  langsearch discovery registers Workday companies, ignores non-ATS: OK")


def test_no_key_skips():
    with patch.object(config, "LANGSEARCH_API_KEY", ""):
        n = langsearch_discovery.discover(["biomedical"], delay=0)
    assert n == 0
    print("  no key -> discovery skips cleanly: OK")


if __name__ == "__main__":
    test_discovery_registers_workday_companies()
    test_no_key_skips()
    print("\nLangSearch discovery tests passed.")
