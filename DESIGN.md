# Job Application Assistant — Design Doc

A free, local-first tool that finds medtech jobs, tracks them in a **Google Sheet**,
and pre-builds a reviewable "application draft" for each one — adapting your resume
text to the role with a local LLM — so applying to Workday jobs becomes: **get a
notification → approve a draft like a PR → do the final submit yourself.**

Status: **Phase 1 built** (job finder → CSV/Sheet; Workday client working & tested).
Phases 2–4 pending. Candidate: Prudhvi Adari — OSU CS + pre-med, biomedical
research & ML; target = medtech.

---

## 1. Goals and non-goals

### Goals
- **Find jobs** from legitimate, free sources and collect them in one place.
- **Track** each job through a pipeline (new → relevant → draft ready → approved → submitted → outcome).
- **Adapt** your real resume content to each role's keywords using a **free local LLM** — rephrase and reorder, never fabricate.
- **Pre-build an application draft** per job: every field pre-filled + adapted resume text, stored for review.
- **One review surface**: you approve/edit/reject a draft like reviewing a pull request.
- **Autofill** the live Workday form from an approved draft, then stop so you submit manually.
- **Free and local**: no paid APIs, resume data stays on your machine.

### Non-goals (deliberately out of scope)
- **No auto-submit, ever.** A human always clicks submit. (This is the line that keeps the tool legitimate and your applications high-quality.)
- **No mass-apply bot.** The tool assists *your* applications; it does not blast hundreds of forms.
- **No scraping of hostile sites** (LinkedIn/Indeed/Glassdoor direct scraping). We use official APIs and public JSON endpoints only — see §8.
- **No fabrication.** The LLM never invents employers, dates, titles, degrees, or skills.

### Why "no auto-submit" is a feature, not a limitation
A hands-off applier violates Workday / job-board terms, gets accounts flagged, and
produces low-quality applications that hurt you. Automating *everything up to* submit
gives you ~95% of the time savings with none of that downside.

---

## 2. The core idea: an application as a reviewable draft

The whole system is organized around one object — the **Application Draft** — and
treating it like a PR:

```
  JOB FOUND ──▶ RELEVANCE CHECK ──▶ DRAFT BUILT ──▶ 🔔 NOTIFY YOU
                                                         │
                                                         ▼
                                              YOU REVIEW THE DRAFT
                                              (approve / edit / reject)
                                                         │
                                                   approved │
                                                         ▼
                                           AUTOFILL LIVE WORKDAY FORM
                                                         │
                                                         ▼
                                              YOU CLICK SUBMIT (manual)
```

A draft contains: the job, a relevance score + reason, every field value the tool
will put into the form, and the **adapted resume text with a diff against your
original** so you can see exactly what the model changed before approving.

---

## 3. Architecture overview

Four components, all free, mostly local:

```
┌──────────────────────────────────────────────┐
│              YOUR MACHINE (local)              │      ┌─────────────────────┐
│                                                │      │   GOOGLE SHEET      │
│  ┌───────────────┐      ┌───────────────────┐ │      │  (store + review)   │
│  │ 1. JOB FINDER │─────▶│ 3. DRAFT BUILDER  │ │      │                     │
│  │   (Python)    │      │ - relevance score │ │◀────▶│  Jobs tab           │
│  │  scheduled    │      │ - resume adapt    │ │ Sheets│  Review tab         │
│  └───────────────┘      │   via Ollama LLM  │ │  API │  Profile tab        │
│         local LLM ◀─────│   (local)         │ │      │  (you Approve here) │
│                         └───────────────────┘ │      └──────────┬──────────┘
└────────────────────────────────────────────────┘                │
                                                    approved draft │ (JSON)
                                                                   ▼
                                                   ┌──────────────────────────┐
                                                   │  4. BROWSER EXTENSION     │
                                                   │  (Manifest V3)            │
                                                   │  fills live Workday form, │
                                                   │  highlights fields, then  │
                                                   │  STOPS for your submit    │
                                                   └──────────────────────────┘
```

Why these choices:
- **Python** for finder + draft builder: best ecosystem for HTTP, parsing, and talking to Ollama.
- **Google Sheets** as the store **and** the review surface: you already live in Sheets,
  so approving a draft is just changing a cell. Free Google Sheets API. (The finder and
  builder are the only things writing to it; you approve by hand.)
- **Ollama + Qwen3 8B** for adaptation: free, offline, strong instruction-following. Phi-4-mini fallback for low RAM.
- **Browser extension (Manifest V3)** for Workday autofill: runs in your real logged-in session (no bot-detection fight), acts only when you click, and naturally stops before submit.

### One tradeoff to know about Sheets
A spreadsheet cell can't render a nice red/green inline diff. So for the adapted
resume text, the Review tab holds the **adapted version in one column and your
original in the neighboring column**, side by side, so you can still see exactly
what changed before approving. (If you ever want a true inline diff, that's the
one thing the local-web-UI option did better — noted, not blocking.)

---

## 4. Data model (Google Sheet)

One Google Sheet with three tabs. The finder + builder write via the Sheets API;
you review by editing cells.

### Tab 1 — `Jobs` (every job found; the "spine")
| Column | Meaning |
|---|---|
| `job_key` | `source + ':' + source_job_id` — the dedup key (finder skips rows that already exist) |
| `source` | `adzuna` \| `workday` \| `greenhouse` \| `lever` |
| `company` | employer |
| `title` | role title |
| `location` | city/state or "Remote" |
| `url` | the apply/listing URL (for Workday, the real apply page) |
| `description` | full JD text (used by scorer + adapter; can be a short excerpt + link) |
| `posted_at` / `found_at` | dates |
| `status` | `new → relevant → draft_ready → approved → filled → submitted → rejected/offer/skipped` |
| `relevance_score` | 0–1 from the scorer |
| `relevance_reason` | one-line "why it matched" |

### Tab 2 — `Review` (one row per draft-ready job — where you approve)
| Column | Meaning |
|---|---|
| `job_key` | links back to `Jobs` |
| `company` / `title` / `url` | quick context |
| `relevance_score` / `relevance_reason` | why it's here |
| `ring` | priority ring 1–4 (§6.7): core-medicine / medical-AI / adjacent-tech / off-path |
| `fit_score` / `path_score` | can-he-do-it × does-it-serve-medicine (§6.7) |
| `fit_verdict` | advisor's verdict + reason (§6.6) |
| `role_mode` | "summer internship" / "night-weekend clinical" |
| `positioning_advice` | what to emphasize for this role |
| `gaps` | gaps to address or acknowledge |
| `next_action` | advisor suggestion: apply / apply + outreach / skip |
| `adapted_summary` | LLM-tailored summary **(editable)** |
| `original_summary` | your base summary, side-by-side for comparison |
| `adapted_bullets` | tailored bullets **(editable)** |
| `original_bullets` | your real bullets, side-by-side |
| `other_fields_json` | the rest of the form values the extension will fill |
| **`APPROVE?`** | **you set this**: `approve` / `edit` / `reject`. This is your PR-review cell. |

### Tab 3 — `Profile` (your single source of truth — §5)
Stored as a single JSON blob in one cell (easiest), or expanded into labeled rows.

**`status` is the spine.** Finder writes `new`; the builder scores, and for jobs over
your threshold writes `draft_ready` + a `Review` row + fires a notification; you set
`APPROVE?`; the extension reports `filled`; you record the final outcome.

---

## 5. The profile: single source of truth

One structured JSON object. Both resume adaptation and form autofill read from it,
which is what makes everything consistent. This also **fixes your Workday render
problem**: instead of Workday parsing your PDF (which it does badly), we fill the
structured fields directly from this profile, and attach the PDF only as the
file upload.

Below is the profile **pre-filled from your resume** — this is a real starting point,
not a template. You'd only need to fill the blanks (EEO/standard answers) and correct
anything I misread.

```json
{
  "basics": {
    "first_name": "Prudhvi", "last_name": "Adari",
    "email": "adari.prudhvi.k@gmail.com", "phone": "(740) 803-3006",
    "location": { "city": "Columbus", "state": "OH", "country": "USA" },
    "links": {
      "linkedin": "linkedin.com/in/padari",
      "github": "github.com/prudhviadari-osu",
      "portfolio": ""
    },
    "work_authorization": "US Permanent Resident", "requires_sponsorship": false
  },
  "summary": "OSU Computer Science & Engineering honors student on a pre-medical track with hands-on biomedical research and applied ML experience spanning medical imaging, organ-assessment pipelines, and injury biomechanics.",
  "experience": [
    {
      "company": "Injury Biomedical Research Center (IBRC)", "title": "Undergraduate Research Assistant",
      "start": "2026-09", "end": "present", "location": "Columbus, OH",
      "bullets": [
        "Trained in BSL-2 protocols, DXA/CT imaging workflows, scalpel technique, and PMHS handling for injury biomechanics research.",
        "Developing a MATLAB-usable simulation and visualization tool integrating the MS-Human-700 model, MuJoCo physics simulation, and Vicon motion-capture data; exploring Mimics for anatomical modeling."
      ]
    },
    {
      "company": "The Breathing Association", "title": "Clinical Volunteer",
      "start": "2026-07", "end": "present", "location": "Columbus, OH",
      "bullets": [
        "Accumulated ~100 hours supporting patient intake, working under and reporting to the attending physician.",
        "Developing a patient-facing clinic website and exploring athenahealth integration for scheduling and records."
      ]
    },
    {
      "company": "The Ohio State University (COE-SURE)", "title": "Summer Research Fellow",
      "start": "2026-05", "end": "2026-08", "location": "Columbus, OH",
      "bullets": [
        "Extended a BioHack prototype into an AI-assisted pipeline for donor-kidney assessment and monitoring during normothermic machine perfusion.",
        "Built a calibrated XGBoost donor-risk classifier (>95.5% precision) to flag viable kidneys for re-evaluation instead of default discard; built real-time organ-monitoring alerts; presented at the COE-SURE Research Symposium."
      ]
    },
    {
      "company": "James Cancer Center", "title": "Research Collaborator (Dr. Simeng Zhu)",
      "start": "2026-02", "end": "2026-05", "location": "Columbus, OH",
      "bullets": [
        "Developed ML models to identify and outline brain tumors on MRI for the MICCAI BraTS Challenge using Ohio Supercomputer Center resources."
      ]
    },
    {
      "company": "Handshake AI Fellowship", "title": "Multimedia Analyst",
      "start": "2025-11", "end": "present", "location": "Remote",
      "bullets": [
        "Annotated image, video, and audio datasets; refined labeling guidelines and QA protocols for consistent, high-precision data."
      ]
    }
  ],
  "projects": [
    { "name": "At-Home NG-Tube Management System (BioHack OSU)", "date": "2026-10",
      "bullets": [
        "Led ideation for a three-part at-home NG-tube concept: securement clip, dual-sensing analyzer, and caregiver/clinician app.",
        "Designed a handheld pH/CO2 dual-sensing enteral tube analyzer concept to support tube-placement assessment."
      ] },
    { "name": "Learn++ — AI-Assisted Learning Platform (BuildX)", "date": "2026-10",
      "bullets": [
        "Co-developed an AI-assisted learning platform; contributed to backend/API, AI learning features, study scheduling, gamification, and product direction.",
        "Presented at Construct I/O; advancing through BuildX and coordinating with OSU ETS toward a Carmen integration."
      ] }
  ],
  "education": [
    { "school": "Ohio State University", "degree": "BS", "field": "Computer Science and Engineering (University Honors; Pre-Medical Track)",
      "end": "2029-06", "gpa": "3.85" }
  ],
  "awards": [
    "HackOHI/O 2026 — Honda Track, 1st Place (Learn++)",
    "HackAI 2026 — Energy Track, 1st Place (Dual-Branch LSTM energy forecasting; invited to TDAI AI Research Summit)",
    "MakeOHI/O 2026 — Intel UPW Track, 2nd Place (sensor dashboard + CAD filter cartridge)",
    "Flextronics Engineering Collaborative — Grant Recipient (prosthesis concept)"
  ],
  "skills": {
    "programming": ["Python (OpenEDG certified)", "Java", "MATLAB", "Git/GitHub"],
    "biomedical_research": ["DXA/CT imaging", "Osiris", "BSL-2 protocols", "PMHS handling", "scalpel technique", "Materialise Mimics (workflow exposure)"],
    "machine_learning": ["NumPy", "Pandas", "Scikit-learn", "XGBoost", "PyTorch", "TensorFlow"]
  },
  "eeo": { "gender": "Male", "veteran": "Not a protected veteran", "disability": "No", "race": "leave blank / per-application" },
  "preferences": {
    "target": "Summer 2027 internships; ALSO open to night/weekend clinical roles year-round (for clinical hours)",
    "earliest_start_date": "Summer 2027 for internships; clinical roles available sooner (evenings/weekends)",
    "locations": {
      "primary": ["Columbus, OH", "Remote"],
      "summer_only": "open to other areas for summer internships",
      "relocate": "summer internships only"
    },
    "salary_expectation": "no expectation / leave blank"
  },
  "standard_answers": {
    "why_this_company": "template or blank — advisor drafts per application"
  },
  "resume_pdf_path": "/path/to/Prudhvi_Adari_Resume.pdf"
}
```

The profile is now fully populated from your resume + your answers — no `TODO`s left
(race is left blank since EEO is optional; the advisor drafts "why this company" per
application). This single object feeds resume adaptation, the advisor, keyword
expansion, and form autofill — which is what **fixes your Workday render problem**: we
fill the structured fields directly from here and attach your PDF only as the upload,
so Workday never has to (badly) parse the PDF into fields.

Two preference rules the finder + advisor enforce from the profile:
- **Two role modes:** (a) Summer 2027 internships, and (b) night/weekend clinical
  roles year-round (for clinical hours). The finder searches both; the advisor tags
  which mode a job fits.
- **Location logic:** Columbus + Remote always; other locations only when the role is
  a summer internship.

---

## 6. Resume adaptation (the local LLM)

### Model
- **Default: `qwen3:8b` via Ollama** — free, offline, strong at "follow these constraints" rewriting. ~5 GB download, needs ~8 GB RAM.
- **Low-RAM fallback: `phi4-mini` (3.8B)** — runs in ~4 GB.
- Install is one step (`ollama pull qwen3:8b`); the Python side calls `http://localhost:11434`. No API key, nothing leaves your machine.

### What it does (and strictly does not do)
Input: your `profile.experience` bullets + `profile.summary`, plus the job description.
Output: **rephrased and reordered** bullets + a tailored summary that surface the
real experience most relevant to this job, using the job's own terminology where honest.

Hard rules baked into the prompt and enforced in code:
- **Never invent** companies, titles, dates, degrees, numbers, or skills you don't have.
- Only rephrase/reorder/emphasize content that already exists in the profile.
- Return **structured JSON** (so we can diff it field-by-field), low temperature for structure.
- Every change is shown to you as a **diff vs. your original** in the review surface — you approve, edit, or reject per item.

### Prompt shape (sketch)
```
SYSTEM: You rephrase a candidate's real resume to match a job. You MUST NOT invent
        any employer, title, date, credential, metric, or skill not present in the
        input. Only reword, reorder, and re-emphasize existing content. Output JSON
        matching the given schema. If nothing honestly matches, return the original.

USER:   <job description>
        <candidate profile JSON>
        <output schema>
```

A deterministic post-check compares the output against the input (entity/skill set
must be a subset; dates/companies unchanged) and rejects any draft that fails,
before it ever reaches you.

### Relevance scoring (same model, cheap pass)
Before building a full draft, a quick pass scores the job 0–1 against your profile
and writes a one-line reason ("Strong: Python + data pipelines match 4/5 must-haves").
Only jobs above a threshold you set get a full draft built and trigger a notification.
The scorer also applies your preference rules (role mode + location logic from §5).

---

## 6.5 Interactive search + keyword expansion

A you-driven search mode on top of the standing scheduled searches. You look for a
variety of things, so instead of a fixed query list, you can run an ad-hoc search
whenever you want and let the model widen it.

Flow:
1. You enter a few seed keywords, e.g. `biomedical, imaging, ML`.
2. The **same local model** expands them into related medtech terms it associates
   with your field — e.g. `medical imaging, computer vision, radiology AI, MRI/CT,
   clinical data scientist, research associate, bioinformatics, biomechanics`.
3. **You see the expanded list and prune it** before anything runs (same
   human-in-the-loop principle — the model proposes, you approve the search terms).
4. The finder runs every approved term across all sources (Adzuna + the Workday seed
   companies + Greenhouse/Lever) and layers results into the `Jobs` tab, deduped
   against what's already there.

This reuses the model you're already running — it's just a different small prompt
("given these seeds and this profile, suggest related job-search keywords; output a
JSON list"). Low temperature, bounded list length.

**Honest limit:** an 8B local model is decent but not brilliant at term expansion —
expect the occasional off term. That's exactly why step 3 (you prune) exists. Useful,
not magic.

---

## 6.6 The advisor (the model has a point of view)

The model doesn't just fill forms — for each relevant job it acts as a **first-pass
job-hunt advisor**, because it already has your full profile *and* the job description,
so its advice is grounded in real specifics rather than generic platitudes. Per job it
produces (stored on the `Review` row, shown before you approve):

- **Fit verdict + reason** — e.g. "Strong: your BraTS/MRI tumor-segmentation work maps
  directly to this imaging-AI role" or "Stretch: they want 3+ yrs industry — lead with
  research depth and hackathon wins."
- **Role mode tag** — "Summer 2027 internship" vs "night/weekend clinical" (per §5).
- **Positioning advice** — which experiences to emphasize/de-emphasize for *this* role.
- **Gaps to address** — e.g. "no regulatory/FDA exposure mentioned — acknowledge or skip."
- **Suggested next action** — `apply` / `apply + reach out to {person/team}` / `skip (too senior)`.
- **A drafted "why this company" paragraph** you can edit.

Every piece of advice is required to **cite the specific profile/JD facts it's based
on**, so you can judge whether it's right rather than trusting it blind.

**Honest limit:** an 8B local model gives useful, directionally-right advice — treat it
as a smart friend's quick take for triage, not a career coach's final word. If you ever
want sharper advice, the advisor sits behind the same swappable `Adapter` interface, so
a stronger model could be slotted in later (that's the only place a paid model might
ever be worth it — your choice, never required).

---

## 6.7 The fit model: priority rings (why a job is surfaced)

The tool should find roles the candidate is a good fit for **even if he didn't search
for them** — but with a sense of priority that mirrors his actual goal. Prudhvi is
**pre-med: medicine is the path, technical roles are welcome when they serve it.** So
every job is scored on *two* axes and ranked by both:

- **fit score** — can he do this job? (skills/experience match)
- **path score** — does this advance a pre-med headed toward medicine (with ML as a tool)?

Ranking uses `fit × path`, so a medical-AI role with medium skill-match outranks a
perfect-match non-medical ML job. Jobs are tagged with a **priority ring**:

| Ring | What | How it's treated |
|---|---|---|
| **1 — Core medicine / clinical** | clinical roles, research assistant, patient exposure, hospital/health-system, anything giving clinical hours | Highest priority. Night/weekend clinical roles (role-mode §5) live here. |
| **2 — Medical AI / medtech / biomedical** | medical imaging AI, clinical-data science, medical-device R&D, bioinformatics, health-tech | **Equal top priority** — ML skills *and* medical direction both apply. |
| **3 — Adjacent technical (off-path)** | general ML / data science / research engineering with no medical angle | **Surfaced but deprioritized** — shown lower, clearly labeled "off-path: no clinical hours / medical exposure." Visible, never crowds out rings 1–2. |
| **4 — Off-path non-technical** | unrelated SWE/sales/etc. | Filtered out / buried. |

**Decision: boundary = option A** — lead with medicine, keep medical-AI/medtech equal,
let genuinely good pure-tech roles appear but stay in their lane. The advisor labels
every ring-3 job with an honest "this won't give you clinical hours or medical
exposure" note so nothing misleads him toward off-goal applications.

### What this changes in the build (Phase 2)
1. **Profile-driven keyword expansion (§6.5)** is tuned to the rings: medicine +
   medical-AI heavy, general-technical as a secondary layer the user can prune.
2. **Company sourcing widens beyond medtech**: health systems + medtech + medical-AI
   companies first (rings 1–2), select tech/research orgs second (ring 3). Each company
   in the config carries a ring hint.
3. **The advisor becomes a ring-aware fit-finder**: it assigns ring + fit + path, and
   the surprising-but-good matches float up *with a reason* ("Ring 2 — not what you
   searched, but your BraTS/MRI work is exactly this imaging-AI role").

---

## 7. The review surface: the Google Sheet `Review` tab

Reviewing happens **in the Sheet** (§4, Tab 2). The flow:

1. The builder adds a row to `Review` for each draft-ready job and **fires a
   notification** (desktop notification and/or a daily email/summary — your choice).
2. You open the `Review` tab. Each row shows the job, the score + reason, and the
   **adapted text beside your original** (side-by-side columns, since a cell can't do
   an inline diff).
3. You either accept as-is or edit the `adapted_*` cells directly, then set the
   **`APPROVE?`** cell to `approve` (or `edit` / `reject`). That cell *is* your
   "merge the PR" action.
4. The extension (§10) only ever pulls rows where `APPROVE?` = `approve`.

This keeps everything in the one tool you already use daily, and the approval is a
single, deliberate cell edit per job — no separate app, no accounts beyond Google.

*(If you later want a true inline red/green diff or a kanban/mobile view, a tiny local
web UI or a Notion mirror can read the same Sheet. Noted as optional, not needed to start.)*

---

## 8. Job sources (all free, all legitimate)

| Source | Type | Why | Notes |
|---|---|---|---|
| **Adzuna API** | Aggregator, free tier | Broad medtech keyword/location search; often links straight to the Workday apply URL — good for *discovering* new companies | Free API key |
| **Workday company search** | Per-company JSON | Hits each target company's *own* public careers endpoint (`/wday/cxs/{tenant}/{site}/jobs`) | Public, per-tenant |
| **Greenhouse public boards** | Per-company JSON | Medtech firms on Greenhouse; `boards-api.greenhouse.io/v1/boards/{co}/jobs` | No key |
| **Lever public postings** | Per-company JSON | Same idea for Lever employers | No key |

Explicitly **not** scraping LinkedIn / Indeed / Glassdoor directly (TOS + bans).

### How the finder discovers Workday URLs (your main question)

There is **no global directory of all Workday jobs** — Workday is per-tenant, each
company hosts its own careers site. But every one of those sites is a JavaScript app
backed by a **public JSON endpoint**, and that's what we call:

```
POST https://{tenant}.{dc}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Body: {"appliedFacets":{}, "limit":20, "offset":0, "searchText":"biomedical"}
```

- No API key, no login, no headless browser.
- Returns up to **20 postings per page** — each with title, location text, a "posted"
  label, a requisition ID, and an `externalPath`. The job's real apply URL is
  `https://{tenant}.{dc}.myworkdayjobs.com/{site}` + `externalPath`.
- Page through with `offset`. **Known limits to respect:** a ~2,000-result ceiling per
  query and an offset that can loop, so searches are scoped by keyword/location to
  stay well under the cap.

So discovery works in two complementary ways:
1. **Per-company polling (precise):** we keep a seed list of medtech companies +
   their `{tenant}/{dc}/site}` and search each one for your keywords.
2. **Aggregator discovery (broad):** Adzuna surfaces medtech postings across many
   employers and frequently hands us the Workday apply URL directly — which also tells
   us about Workday companies we didn't have in the seed list, so we can add them.

### Medtech Workday seed list (starting point, verified on Workday)
Medtronic, Pfizer, Novartis, Amgen, Regeneron, Bristol Myers Squibb, Takeda,
AstraZeneca, IQVIA, Labcorp. (We'll resolve each one's exact `{tenant}.{dc}` +
site slug when we build the finder — I verify each by loading its careers site once.)
Add/remove companies freely; it's just a config list. Good fits for your profile also
include device/imaging firms (GE HealthCare, Siemens Healthineers, Stryker, Boston
Scientific, Abbott) — we'll confirm which of those are on Workday vs. another ATS.

The finder normalizes every source into the `Jobs` tab schema, dedupes on `job_key`,
and appends only new rows.

---

## 9. Component contracts (so pieces stay swappable)

- **Finder → Sheet**: writes `Jobs` rows. Each source is a plugin exposing
  `fetch(query) -> list[NormalizedJob]`. Adding a source = adding one plugin.
- **Draft builder → Sheet**: reads `new` jobs + `Profile`, writes `relevance_score`,
  `relevance_reason`, and (for jobs over threshold) a `Review` row + `status=draft_ready`.
  The LLM sits behind an `Adapter` interface (`adapt(profile, jd) -> AdaptedResume`) so
  the local model can be swapped for another backend later.
- **You ↔ Sheet**: you read the `Review` tab and set `APPROVE?`.
- **Sheet → Extension**: the extension pulls rows where `APPROVE?=approve` as a draft
  JSON (via the Sheets API read, or a small local export the builder writes). Contract
  = the draft JSON schema (fields + adapted text). Pinned before we build the extension.
- **Extension → Sheet**: writes `status=filled` back so the pipeline knows it reached the form.

---

## 10. The Workday autofill (browser extension)

- **Manifest V3** Chrome/Edge extension, content script scoped to `*.myworkdayjobs.com` / `*.myworkdaysite.com`.
- Reads the approved draft, maps values onto Workday's form fields.
- Workday is the *most* automatable ATS because fields carry stable
  `data-automation-id` attributes across tenants
  (e.g. `legalNameSection_firstName`, `email`, `phone-number`), so a mapping table
  covers most of the standard "My Information" / "My Experience" pages.
- Multi-step applications: fill the current step, highlight filled fields, let you
  click "next" yourself (keeps you in control across pages).
- Attaches your PDF to the resume upload (so the ugly auto-parse is bypassed — the
  structured fields are already correctly filled from the profile).
- **Stops before submit. Always.** It highlights everything it touched and waits.

Field-mapping maintenance (Workday tenants vary slightly) is the main ongoing cost;
the mapping lives in one config so it's easy to patch.

---

## 11. Security, privacy, legal boundaries

- **Mostly local.** The finder, builder, and local LLM run on your machine; resume
  *adaptation* happens locally so your resume text never goes to a third-party model.
  The one thing that leaves your machine is the data written to **your own private
  Google Sheet** (jobs + profile + drafts) over the Google Sheets API — it stays in
  your Google account. No paid APIs.
- **Human submit gate is permanent** — the tool never submits. This keeps you
  compliant with Workday / job-board terms and keeps quality high.
- **Respect robots/TOS**: only official APIs + public JSON endpoints; polite rate
  limiting on the finder; no hostile-site scraping.
- **Secrets** (Adzuna/USAJobs free keys) in a local `.env`, never in code.
- **No fabrication** enforced in code, not just in the prompt.

---

## 12. Phased build plan

Each phase is independently useful — you get value before the whole thing exists.

- **Phase 1 — Finder → Google Sheet.** Python finder: Adzuna (medtech keywords) +
  the Workday `cxs` client polling 2–3 seed companies (e.g. Medtronic, IQVIA) →
  `Jobs` tab with dedup. *Outcome: medtech jobs (with their Workday apply URLs)
  collecting themselves in your Sheet. Zero legal risk.*
- **Phase 2 — Profile + local LLM adaptation + relevance scoring.** Load the profile
  (pre-filled from your resume, §5), wire up Ollama/Qwen3, generate adapted text +
  scores with the subset/no-fabrication check; write `Review` rows for jobs over
  threshold. *Outcome: tailored, side-by-side text you could already copy by hand.*
- **Phase 3 — Notifications + the review loop.** Fire a notification when new
  `Review` rows appear; wire the `APPROVE?` cell as the gate. *Outcome: the full
  "notify → approve a draft in the Sheet" loop, minus autofill.*
- **Phase 4 — Workday extension.** Autofill an approved draft into a live Workday form,
  attach the PDF, stop before submit, report `filled` back. *Outcome: the complete
  assisted-apply flow.*
- **Phase 5 (optional) — niceties.** Auto-parse the resume PDF into the profile,
  Notion mirror / inline-diff view, more sources, more ATSes (Greenhouse/Lever forms).

Recommended first build: **Phase 1**, because it proves the Sheet schema + the Workday
discovery and gives you a working medtech job tracker immediately.

---

## 13. Open questions to settle before/along the build
1. **Google Cloud setup** for the Sheets API — FREE (no billing; well under free
   quota). One-time ~10-min setup: create a project, enable the Sheets API, download a
   service-account credentials file, share your Sheet with the service account email.
   Exact steps provided during Phase 1.
2. **Which medtech companies to seed first** from the §8 list (pick 2–3 to start —
   e.g. Medtronic + IQVIA + one you care about)?
3. **Relevance tuning:** your must-have keywords/roles (e.g. "biomedical", "clinical
   data", "machine learning", "imaging", "research"), locations (Columbus / remote /
   anywhere?), and a score threshold (e.g. only build drafts for jobs ≥ 0.6)?
4. **Fill the profile `TODO`s** (work authorization, EEO if you want it, standard
   answers) — want to do that now, or leave blanks and fill per-application?
```

</invoke>
