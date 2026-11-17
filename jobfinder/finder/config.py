"""Everything you tune lives here. No code changes needed to adjust the search.

Values are pre-filled for Prudhvi's medtech search (DESIGN.md). Edit freely.
"""

# ---------------------------------------------------------------------------
# What to search for
# ---------------------------------------------------------------------------
# Seed keywords. In Phase 1 these are used directly; in Phase 2 the local model
# can expand them (interactive search, DESIGN.md §6.5).
KEYWORDS = [
    "biomedical",
    "medical imaging",
    "machine learning",
    "clinical data",
    "research",
    "bioinformatics",
]

# ---------------------------------------------------------------------------
# Location / role preferences (DESIGN.md §5)
# ---------------------------------------------------------------------------
# Always acceptable locations (matched case-insensitively as substrings).
LOCATIONS_PRIMARY = ["columbus", "remote", "ohio"]
# Other locations are accepted ONLY for summer-internship-type roles.
ALLOW_OTHER_LOCATIONS_FOR_INTERNSHIPS = True
# Words in a title that mark a role as a summer internship.
INTERNSHIP_HINTS = ["intern", "internship", "summer", "co-op", "coop"]
# Words that mark a night/weekend clinical role (acceptable year-round, any OH/remote loc).
CLINICAL_HINTS = ["clinical", "patient", "volunteer", "per diem", "evening", "weekend", "night"]

# ---------------------------------------------------------------------------
# Workday seed companies (DESIGN.md §8)
# ---------------------------------------------------------------------------
# Each entry: tenant + data-center (dc) + site slug of a company's Workday
# careers site. The job search endpoint is:
#   https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
#
# These are placeholders with the correct STRUCTURE. The exact tenant/dc/site
# for each company is verified by `python -m finder.resolve_workday <careers-url>`
# (prints the three values from a careers URL you paste). Start with 1-2 you've
# confirmed, then add more.
WORKDAY_COMPANIES = [
    # Example confirmed-structure entries — replace dc/site after resolving:
    # {"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"},
    # {"name": "IQVIA",     "tenant": "iqvia",     "dc": "wd1", "site": "IQVIA"},
]

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
# "csv" (default, zero setup) or "sheets".
DEFAULT_SINK = "csv"
CSV_PATH = "jobs.csv"

# Google Sheets (only used when --sink sheets). Free; see README.
GOOGLE_SHEET_ID = ""            # the long id from the sheet URL
GOOGLE_CREDS_PATH = "google_creds.json"
GOOGLE_WORKSHEET = "Jobs"

# ---------------------------------------------------------------------------
# Optional source credentials (leave blank to skip that source)
# ---------------------------------------------------------------------------
# Free key from https://developer.adzuna.com/ (App ID + App Key, no billing).
# With a key set, Adzuna provides broad medtech discovery AND auto-registers any
# Workday companies it finds (saved to discovered_companies.json) so the Workday
# source polls their full boards on future runs.
ADZUNA_APP_ID = ""
ADZUNA_APP_KEY = ""
ADZUNA_COUNTRY = "us"
# Greenhouse/Lever need only a company board slug, no key (added per-company later).
GREENHOUSE_COMPANIES: list[str] = []
LEVER_COMPANIES: list[str] = []

# Where auto-discovered Workday companies are saved (blank = default file).
DISCOVERED_COMPANIES_PATH = ""

# Politeness: seconds to sleep between HTTP calls.
REQUEST_DELAY_SECONDS = 0.5
