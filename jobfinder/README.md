# Job Finder — Phase 1

The first slice of the Job Application Assistant (full plan in [`../DESIGN.md`](../DESIGN.md)):
it finds medtech jobs — including the ones behind Workday career sites — and
collects them, deduped, into a CSV or your Google Sheet.

It is **runnable with zero setup**: with no API keys at all it runs cleanly and
tells you what to add. Add a free Adzuna key and/or a Workday company to start
getting real jobs.

---

## Table of contents
1. [What it does](#what-it-does)
2. [How company discovery works](#how-company-discovery-works)
3. [Setup (step by step)](#setup-step-by-step)
4. [Running it](#running-it)
5. [Getting a free Adzuna API key](#getting-a-free-adzuna-api-key)
6. [Adding Workday companies](#adding-workday-companies)
7. [Output: CSV (default) or Google Sheets](#output-csv-default-or-google-sheets)
8. [Configuration reference](#configuration-reference)
9. [Running the tests](#running-the-tests)
10. [Project layout](#project-layout)
11. [Troubleshooting](#troubleshooting)

---

## What it does

Pulls medtech jobs from:

- **Adzuna** (broad aggregator) — searches many employers for your keywords, and
  **auto-discovers Workday companies**: any Adzuna result whose apply URL is a
  `*.myworkdayjobs.com` link gets its company parsed out and saved to
  `discovered_companies.json`, so the Workday source polls that company's full board
  on the next run. *(Needs a free Adzuna key — see below.)*
- **Workday** company career sites, via each company's public JSON endpoint
  (`/wday/cxs/{tenant}/{site}/jobs`) — this is where the real Workday apply URLs come
  from. Polls both your seed list **and** the auto-discovered companies.
- *(Greenhouse / Lever use the same plugin interface — added in a later phase.)*

Then it:
- Normalizes every source into one row shape.
- Dedupes on a stable `job_key` so re-runs only add genuinely new jobs.
- Applies your location/role preferences (Columbus + Remote always; other locations
  only for summer internships; night/weekend clinical tagged separately).
- Writes to `jobs.csv` (default) or a Google Sheet.

## How company discovery works

There is **no global directory of Workday companies** — each company hosts its own
Workday site. We find them two ways:

1. **Seed list** — companies you name in `WORKDAY_COMPANIES` (`finder/config.py`).
2. **Auto-discovery** — Adzuna surfaces medtech jobs across many employers; the ones
   hosted on Workday expose their careers URL, which we parse and register
   automatically into `discovered_companies.json`.

So searching gradually grows the Workday company list by itself.

---

## Setup (step by step)

**Prerequisites:** Python 3.10+ (`python3 --version` to check).

### 1. Get the code
```bash
git clone https://github.com/prudhviadari-osu/jobfinder.git
cd jobfinder
```

### 2. Create a virtual environment and install dependencies
A virtualenv keeps these packages isolated from your system Python.

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You'll know it worked if your prompt now shows `(.venv)`. The only required
dependency is `requests`.

### 3. (Optional) Add an Adzuna key and/or a Workday company
Nothing is required to run, but you need at least one source configured to get real
jobs. See [Getting a free Adzuna API key](#getting-a-free-adzuna-api-key) and
[Adding Workday companies](#adding-workday-companies) below.

---

## Running it

With the virtualenv active:

```bash
python -m finder.run                       # uses KEYWORDS from config, writes jobs.csv
python -m finder.run --keywords imaging ml # override keywords for this run only
python -m finder.run --sink sheets         # write to your Google Sheet instead of CSV
```

Open `jobs.csv` to see results. Re-running is safe — only new jobs are appended.

With **no** keys/companies configured, you'll see a clean run that explains what to
add (it won't error):
```
  [adzuna]  no API key set — skipping. Add ADZUNA_APP_ID / ADZUNA_APP_KEY ...
  [workday] no companies configured — add entries to WORKDAY_COMPANIES ...
```

---

## Getting a free Adzuna API key

**Adzuna** is a job-search aggregator with a free developer API. Free tier: ~2,500
calls/month (250/day), no credit card. For us it's the broad medtech net **and** the
Workday-company discovery layer.

1. Go to **https://developer.adzuna.com/** and sign up.
2. Register an app — you'll get an **App ID** and an **App Key** (two strings).
3. Open `finder/config.py` and paste them in:
   ```python
   ADZUNA_APP_ID  = "your-app-id"
   ADZUNA_APP_KEY = "your-app-key"
   ADZUNA_COUNTRY = "us"
   ```
4. Run `python -m finder.run`. You'll see Adzuna results in `jobs.csv` and any
   discovered Workday companies in `discovered_companies.json`.

---

## Adding Workday companies

You don't have to guess a company's `tenant`/`dc`/`site` — a helper figures it out
from the careers URL and live-tests the endpoint.

1. Find the company's Workday careers URL (looks like
   `https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers`).
2. Run:
   ```bash
   python -m finder.resolve_workday https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers
   ```
   It prints a ready-to-paste config line and confirms the endpoint responds:
   ```
   Add this to WORKDAY_COMPANIES in finder/config.py:
       {"name": "Medtronic", "tenant": "medtronic", "dc": "wd1", "site": "MedtronicCareers"},
   Testing endpoint:
     OK — endpoint live. total jobs reported: 1843
   ```
3. Paste that line into `WORKDAY_COMPANIES` in `finder/config.py`.
4. Run `python -m finder.run`.

Companies auto-discovered via Adzuna are added to `discovered_companies.json`
automatically — you don't need to do anything for those.

**Medtech starter companies to try:** Medtronic, IQVIA, Labcorp, Amgen, Regeneron,
Bristol Myers Squibb, Takeda, AstraZeneca, Novartis, Pfizer.

---

## Output: CSV (default) or Google Sheets

### CSV (default, zero setup)
Writes `jobs.csv` in the project folder. Nothing to configure.

### Google Sheets (free, optional)
1. Create a free **Google Cloud project**: https://console.cloud.google.com/
2. Enable the **Google Sheets API** for that project
   (APIs & Services → Library → "Google Sheets API" → Enable).
3. Create a **service account** (APIs & Services → Credentials → Create credentials →
   Service account). Create a **JSON key** for it and download the file.
4. Save that file as `google_creds.json` inside the `jobfinder/` folder.
5. Create a Google Sheet. From its URL, copy the long ID between `/d/` and `/edit`:
   `https://docs.google.com/spreadsheets/d/`**`THIS_IS_THE_ID`**`/edit`
6. **Share the Sheet** with the service account's email (it's the `client_email` in
   `google_creds.json`), giving it **Editor** access.
7. In `finder/config.py` set `GOOGLE_SHEET_ID = "THE_ID_FROM_STEP_5"`.
8. Install the two extra packages and run:
   ```bash
   pip install gspread google-auth
   python -m finder.run --sink sheets
   ```

The jobs appear in a `Jobs` tab (created automatically if missing), deduped the same
way as the CSV.

> **Is this free?** Yes. The Google Sheets API and a Google Cloud project cost
> nothing, and a personal job search stays far under the free quota.

---

## Configuration reference

Everything you tune is in **`finder/config.py`** — no code changes needed.

| Setting | What it controls |
|---|---|
| `KEYWORDS` | Default search terms (override per-run with `--keywords`). |
| `LOCATIONS_PRIMARY` | Always-acceptable locations (default: Columbus, Remote, Ohio). |
| `ALLOW_OTHER_LOCATIONS_FOR_INTERNSHIPS` | Allow other locations, but only for internships. |
| `INTERNSHIP_HINTS` / `CLINICAL_HINTS` | Title words that classify a job's role mode. |
| `WORKDAY_COMPANIES` | Seed companies to poll (use `resolve_workday` to fill). |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` / `ADZUNA_COUNTRY` | Adzuna free API key + country. |
| `DEFAULT_SINK` / `CSV_PATH` | Output type (`csv`/`sheets`) and CSV filename. |
| `GOOGLE_SHEET_ID` / `GOOGLE_CREDS_PATH` / `GOOGLE_WORKSHEET` | Google Sheets output. |
| `DISCOVERED_COMPANIES_PATH` | Where auto-discovered companies are saved. |
| `REQUEST_DELAY_SECONDS` | Politeness delay between HTTP calls. |

---

## Running the tests

The sandbox/your machine can run these offline — they mock the HTTP layer with
realistic Adzuna/Workday responses, so no network or keys are needed:

```bash
python tests/test_workday_parsing.py
python tests/test_adzuna_discovery.py
```

They verify: Workday apply-URL assembly, requisition-id capture, dedup, pagination,
preference tagging, Adzuna parsing, and Workday company auto-discovery.

---

## Project layout

```
jobfinder/
├── README.md
├── requirements.txt
├── finder/
│   ├── config.py           # everything you tune
│   ├── run.py              # entry point (python -m finder.run)
│   ├── models.py           # the one normalized job shape + row schema
│   ├── preferences.py      # location/role-mode rules
│   ├── discovery.py        # registry of auto-discovered Workday companies
│   ├── workday_tenant.py   # parse a myworkdayjobs.com URL -> tenant/dc/site
│   ├── resolve_workday.py  # helper: careers URL -> config line + live test
│   └── sources/
│       ├── adzuna.py       # Adzuna search + Workday auto-discovery
│       └── workday.py      # Workday cxs JSON client
└── tests/
    ├── test_workday_parsing.py
    └── test_adzuna_discovery.py
```

---

## Troubleshooting

- **`ModuleNotFoundError: No module named 'requests'`** — your virtualenv isn't
  active or deps aren't installed. Re-run the step 2 commands.
- **`ModuleNotFoundError: No module named 'finder'`** — run from inside the
  `jobfinder/` folder, and use `python -m finder.run` (not `python finder/run.py`).
- **Adzuna returns nothing** — check the key is pasted correctly and you haven't hit
  the daily cap (250/day). Try fewer keywords.
- **`resolve_workday` says FAILED** — the site slug is probably slightly off; open the
  careers page and copy the exact path segment after the domain.
- **Google Sheets: `PermissionError` / 403** — you forgot to share the Sheet with the
  service account's `client_email` (step 6), or didn't give it Editor access.
