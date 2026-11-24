"""Everything you tune lives here. No code changes needed to adjust the search.

Values are pre-filled for Prudhvi's search (DESIGN.md). Goal: medicine is the path,
medical-AI/medtech is equal priority, general-technical roles are welcome but
deprioritized (the "priority rings" in DESIGN.md §6.7). Edit freely.
"""

# ---------------------------------------------------------------------------
# What to search for  (DESIGN.md §6.5 / §6.7 — grouped by priority ring)
# ---------------------------------------------------------------------------
# Phase 1 uses these directly; Phase 2 lets the local model expand them per ring.
# Ring 1 — core medicine / clinical (highest priority)
KEYWORDS_CORE_MEDICINE = [
    "clinical research",
    "research assistant",
    "clinical",
    "patient care",
    "medical scribe",
]
# Ring 2 — medical AI / medtech / biomedical (equal top priority)
KEYWORDS_MEDICAL_AI = [
    "biomedical",
    "medical imaging",
    "clinical data",
    "bioinformatics",
    "medical device",
    "healthcare machine learning",
]
# Ring 3 — adjacent technical, off-path (surfaced but deprioritized)
KEYWORDS_ADJACENT_TECH = [
    "machine learning",
    "data science",
    "research software",
    "computer vision",
]
# The flat list the finder searches (all rings). Prune/extend freely.
KEYWORDS = KEYWORDS_CORE_MEDICINE + KEYWORDS_MEDICAL_AI + KEYWORDS_ADJACENT_TECH

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

# --- US-only filter: drop jobs clearly outside the United States ---
US_ONLY = True
# Location text containing any of these is treated as US (plus the 50 state codes below).
# Positive US signals. NOTE: "remote" is deliberately NOT here — remote isn't
# inherently US ("Remote - EMEA" exists); bare remote is handled separately.
US_LOCATION_HINTS = [
    "united states", "u.s.", "usa", " us ", "us-", "-us", "remote - us",
    "remote, us", "remote us", "columbus", "ohio",
]
US_STATE_CODES = [
    "al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in","ia","ks",
    "ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv","nh","nj","nm","ny",
    "nc","nd","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","vt","va","wa","wv",
    "wi","wy","dc",
]
# Full state names (lowercase) — Workday often shows "Minnesota" not "MN".
US_STATE_NAMES = [
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut",
    "delaware","florida","georgia","hawaii","idaho","illinois","indiana","iowa",
    "kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan",
    "minnesota","mississippi","missouri","montana","nebraska","nevada",
    "new hampshire","new jersey","new mexico","new york","north carolina",
    "north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island",
    "south carolina","south dakota","tennessee","texas","utah","vermont","virginia",
    "washington","west virginia","wisconsin","wyoming",
]
# Clear non-US signals — if present (and no US signal), the job is dropped.
NON_US_HINTS = [
    "ireland","india","china","germany","france","japan","singapore","canada","mexico",
    "united kingdom","uk","brazil","switzerland","netherlands","israel","australia",
    "spain","italy","poland","korea","philippines","costa rica","dominican",
]
# Non-US REGION markers (not countries) that still mean "not US".
NON_US_REGIONS = ["emea", "apac", "latam", "europe", "asia", "international", "global"]

# --- Student-level filter: keep intern/entry/new-grad; drop senior roles ---
STUDENT_LEVEL_ONLY = True
# Title signals of a student / early-career role (keep these).
STUDENT_LEVEL_HINTS = [
    "intern", "internship", "co-op", "coop", "new grad", "new graduate", "graduate",
    "entry level", "entry-level", "associate", "trainee", "apprentice", "student",
    "early career", "fellow", "i ",
]
# Title signals of a senior / experienced role (drop these, even if other hints match).
SENIOR_LEVEL_HINTS = [
    "senior", "sr.", "sr ", "staff", "principal", "lead", "manager", "director",
    "head of", "vp", "vice president", "chief", "iii", "iv", " v ", "architect",
    "expert", "specialist ii", "ii ", "experienced",
]

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
#
# NOTE ON VERIFYING THESE: big medtech firms often use a vanity careers domain
# (e.g. careers.stryker.com) that redirects to their real Workday URL. The exact
# tenant/dc/site can only be confirmed by loading the live site, which is why each
# candidate below is COMMENTED OUT with its likely values. To activate one:
#   1) open the company's "search jobs" page, copy the *.myworkdayjobs.com URL,
#   2) run:  python -m finder.resolve_workday <that-url>
#   3) paste the exact line it prints here and uncomment it.
# The helper live-tests the endpoint so you know it's right before you rely on it.
#
WORKDAY_COMPANIES = [
    # --- ACTIVE: Medtronic's Workday host is verified (medtronic.wd1.myworkdayjobs.com).
    # If the `site` slug ever 404s, run resolve_workday on the live careers URL and fix it.
    {"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"},
    # --- Below are UNVERIFIED candidates (vanity domains that redirect to Workday).
    # Confirm each with:  python -m finder.resolve_workday <the *.myworkdayjobs.com URL>
    # then uncomment the exact line it prints.
    # {"name": "Stryker",            "tenant": "stryker",       "dc": "wd1", "site": "StrykerCareers"},
    # {"name": "Boston Scientific",  "tenant": "bostonsci",     "dc": "wd1", "site": "BSC"},
    # {"name": "Abbott",             "tenant": "abbott",        "dc": "wd5", "site": "abbottcareers"},
    # {"name": "GE HealthCare",      "tenant": "gehealthcare",  "dc": "wd5", "site": "GEHealthCare"},
    # {"name": "Edwards Lifesciences","tenant": "edwards",      "dc": "wd1", "site": "edwards"},
    # {"name": "Baxter",             "tenant": "baxter",        "dc": "wd1", "site": "baxter"},
    # --- Pharma / CRO / diagnostics (research & clinical-data roles) ---
    # {"name": "IQVIA",              "tenant": "iqvia",         "dc": "wd1", "site": "IQVIA"},
    # {"name": "Labcorp",            "tenant": "labcorp",       "dc": "wd1", "site": "External"},
    # {"name": "Amgen",              "tenant": "amgen",         "dc": "wd1", "site": "Careers"},
    # {"name": "Regeneron",          "tenant": "regeneron",     "dc": "wd1", "site": "Regeneron-Careers"},
    # {"name": "Takeda",             "tenant": "takeda",        "dc": "wd3", "site": "takedajobs"},
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

# Arbeitnow: a FREE, no-key discovery feed (Europe/tech-leaning supplement).
# Needs no signup or card. Set False to skip it.
ENABLE_ARBEITNOW = True

# LangSearch: free web-search API used ONLY to DISCOVER Workday companies (not a
# job feed). It finds career-page URLs the per-company APIs then search directly.
# Free key: https://langsearch.com/dashboard . Blank = discovery skipped.
# Only your search keywords leave the machine (no profile/resume data).
LANGSEARCH_API_KEY = ""
ENABLE_LANGSEARCH_DISCOVERY = True
# Greenhouse / Lever: free, no-key, per-company. You provide the board slug —
# the last path segment of the careers URL, which is often NOT the marketing name:
#   Greenhouse: boards.greenhouse.io/<slug>   -> slug
#   Lever:      jobs.lever.co/<slug>          -> slug  (add "eu": True for EU boards)
# Optional "ring" hint (1=core medicine, 2=medical-AI/medtech, 3=adjacent tech)
# helps Phase 2's fit-finder; it's informational in Phase 1.
#
# Many health-tech / medical-AI / biotech startups use Greenhouse or Lever rather
# than Workday, so these widen coverage into rings 1-2 beyond the big Workday firms.
GREENHOUSE_COMPANIES: list[dict] = [
    # {"name": "Tempus",   "slug": "tempus",   "ring": 2},   # medical-AI / precision medicine
    # {"name": "Benchling","slug": "benchling","ring": 2},   # life-sciences R&D software
    # {"name": "Verily",   "slug": "verily",   "ring": 2},   # health / medical AI
]
LEVER_COMPANIES: list[dict] = [
    # {"name": "ExampleBio", "slug": "examplebio", "ring": 2},
    # {"name": "EUHealthco", "slug": "euhealthco", "ring": 2, "eu": True},
]

# Where auto-discovered Workday companies are saved (blank = default file).
DISCOVERED_COMPANIES_PATH = ""

# ---------------------------------------------------------------------------
# Phase 2 — local model (scoring, advisor, keyword expansion). All free/local.
# ---------------------------------------------------------------------------
# Backend: "ollama" (real local model) or "fake" (offline stub for a dry run).
LLM_BACKEND = "ollama"
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:8b"          # low-RAM alternative: "phi4-mini"
# If the model is unreachable, skip scored jobs ("skip") or stop ("raise").
LLM_ON_ERROR = "skip"

# Politeness: seconds to sleep between HTTP calls.
REQUEST_DELAY_SECONDS = 0.5
