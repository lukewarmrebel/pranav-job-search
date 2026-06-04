# Pranav Job Search — Claude Routines (v5 · 2026-06-04)

This repo runs two Claude-driven routines. GitHub Actions only does scraping and Telegram delivery.
Claude does all the intelligent work: scoring, enrichment, Excel generation.

---

## Routine 1 — Morning Job Digest

**Trigger:** User opens a session and says "run job search", "morning digest", or similar.

### Steps

1. **Pull latest data**
   ```bash
   git pull origin master
   ```

2. **Read scraped jobs (Tier 1)**
   - Read `jobs_raw.json` from the local repo (already pulled above)
   - Note `run_date` from the JSON header
   - Filter: keep jobs where `date_posted` is within last **48 hours** of `run_date`, OR `date_posted` is null/None (LinkedIn null-date jobs are recent — include them)
   - Deduplicate by normalised title + normalised company (strip "India", "Pvt Ltd", "Inc", "Ltd" suffixes before comparing)

3. **Run Indeed MCP enrichment (Tier 2) in parallel**
   ```
   mcp__Indeed__search_jobs, country_code=IN:
     1. search="Product Manager AI"               location="Hyderabad"
     2. search="Senior Product Manager"            location="Bangalore"
     3. search="Strategy Consultant BFSI"          location="Hyderabad"
     4. search="Consultant Digital Transformation" location="Bangalore"
     5. search="Business Analyst Insurance"        location="Hyderabad"
   ```
   For top-10 Tier 2 candidates by title score, call `mcp__Indeed__get_job_details` for full JD.
   Deduplicate Tier 1 + Tier 2 combined. Source preference for duplicates: LinkedIn > Glassdoor > Naukri > Indeed.

4. **Score every job** using the rubric below. Skip anything scoring < 55.

5. **Generate Excel** → save to `output/jobs_YYYY-MM-DD.xlsx`
   Use the Excel spec below. Top 30 rows by score descending.

6. **Save scoring index** for interactive Telegram cards
   Write `data/today_jobs.json`:
   ```json
   {
     "date": "YYYY-MM-DD",
     "jobs": [
       {
         "idx": 0,
         "score": 88,
         "title": "Senior Product Manager",
         "company": "Experian",
         "url": "https://...",
         "date": "2026-06-04",
         "role": "Product Manager",
         "location": "Hyderabad",
         "salary": "",
         "site": "linkedin"
       }
     ]
   }
   ```
   Include ALL scored jobs (not just top 30), sorted by score desc, idx 0-based.

7. **Reset daily state files** (new day, clear yesterday's shortlist)
   ```
   data/shortlisted.json  → {"date": "YYYY-MM-DD", "jobs": []}
   data/skipped.json      → {"date": "YYYY-MM-DD", "jobs": []}
   data/manual_jobs.json  → {"date": "YYYY-MM-DD", "entries": []}
   ```

8. **Commit and push** → triggers GitHub Actions to send to Telegram automatically
   ```bash
   git add output/jobs_YYYY-MM-DD.xlsx data/today_jobs.json \
           data/shortlisted.json data/skipped.json data/manual_jobs.json
   git commit -m "digest: job search YYYY-MM-DD"
   git pull origin master --rebase
   git push
   ```

9. **Send Excel to user in chat** via SendUserFile tool (for immediate reference)

---

## Routine 2 — Apply List Generation

**Trigger:** User says "generate apply list", "my apply list", "what should I apply to", or similar.

### Steps

1. **Pull latest state**
   ```bash
   git pull origin master
   ```

2. **Read decisions from repo**
   - `data/shortlisted.json` → jobs marked ✅ Apply
   - `data/skipped.json`     → jobs marked ❌ Reject
   - `data/manual_jobs.json` → URLs pasted manually in Telegram
   - `data/today_jobs.json`  → all scored jobs (for "Pending" status)

3. **Enrich manual URLs** via Indeed MCP
   For each URL in `manual_jobs.json`, call `mcp__Indeed__get_job_details` to get title, company, salary, JD.

4. **Generate Apply List Excel** → save to `output/apply_YYYY-MM-DD.xlsx`

   **Sheet 1 — Apply List** (jobs to action today)
   | # | Source | Score | Role | Title | Company | Location | Date | Salary | Apply URL | Notes |
   - Shortlisted scraped jobs → green rows
   - Manual URL jobs (enriched) → blue rows

   **Sheet 2 — Full Decision Log**
   | # | Decision | Score | Role | Title | Company | Location | Date | Apply URL | Match Reason |
   - All scored jobs from today_jobs.json with Decision:
     - "Apply" — in shortlisted.json
     - "Reject" — in skipped.json
     - "Pending" — not yet acted on
   - Sorted: Apply first, then Pending, then Reject
   - Green = Apply, Yellow = Pending, Red = Reject

   **Sheet 3 — Manual Jobs Detail**
   | # | URL | Title | Company | Location | Salary | JD Summary | Added At |
   - All manually added URLs with enrichment from Indeed MCP

5. **Commit and push** → GitHub Actions sends to Telegram automatically
   ```bash
   git add output/apply_YYYY-MM-DD.xlsx
   git commit -m "apply-list: YYYY-MM-DD"
   git pull origin master --rebase
   git push
   ```

6. **Send Excel to user in chat** via SendUserFile tool

---

## Candidate Profile

### Identity
- **Name:** Pranav Thatavarthi (also: Bharatam Thatavarti Pranav)
- **LinkedIn:** linkedin.com/in/pranav-thatavarthi
- **Location:** Hyderabad, India
- **Total Experience:** 8+ years (TCS 3.5y → GalaxEye 3m → IIM MBA 2y → ICICI Lombard 3y)
- **Education:** MBA — IIM Ranchi (IT Strategy & Analytics), 2023 · B.Tech Mechanical Engineering — GVP, 2017
- **Honours:** National D2C Rank 1 · National Winner, Tata Imagination Challenge · Top 10 ICICI Lombard Intern (presented to CEO)

### Current Role — Product Manager, ICICI Lombard General Insurance (Jun 2023–Present)
Platform: Motor Claims — AI Inspection, Fraud Detection, OEM Integrations, Omnichannel Comms

**Verified achievements (use these for specific Match Reason language):**
- Enabled ₹3.5 Cr+ annualized savings in fraudulent claims by building automated risk engine with 20+ rule checks and 6 ML models (computer vision, NLP, anomaly detection)
- Accelerated policy approval time by 83% by shipping AI vehicle damage detection model; processes 9K+ cases at 92% accuracy; eliminated manual inspection for 60% of cases
- Increased DIY self-inspection adoption from 12% to 30% by resolving 15+ UX friction points and running trust-signal UI experiments on mobile app
- Owned 12-month product roadmap across 5 cross-functional teams (Engineering, Ops, Legal, Data Science, Compliance); shipped 8 features on schedule
- Built omnichannel claim communication automation — WhatsApp, SMS, email triggers at each claim stage
- Managed 15+ OEM API integrations (Maruti, Hyundai, Tata Motors) — built normalisation layer for claim schema translation
- Improved field surveyor TAT by 65% through demand-pattern analytics and SLA governance frameworks
- Built 7+ Power BI dashboards for OKR tracking across 3 business verticals
- Led 5+ parallel workstreams; coordinated fraud detection enhancements yielding 20% improvement in detection precision

**Domain knowledge:**
- P&C Insurance: Motor Claims lifecycle (FNOL → inspection → estimation → settlement)
- Fraud types: Staged accidents, inflated claims, workshop collusion, ghost claims
- IRDAI regulations: Claims timelines, human-in-the-loop AI compliance, DPDP Act 2023
- Financial metrics: Loss ratio, combined ratio, claim leakage, TAT, NPS
- OEM cashless ecosystem; non-network reimbursement workflows

### Prior Roles
- **GalaxEye Space — PM (Jan–Mar 2022):** 0→1 PMF framework; 100+ enterprise applications validated; competitor landscape across 12 global players
- **ICICI Lombard — Strategy Consultant Intern (Apr–Jun 2022):** Benchmarked 15+ P&C products; built pricing model; presented to CEO; Top 10 intern
- **TCS — Data Analyst (Jan 2018–Jul 2021):** 20+ Power BI financial reports; 10+ KPIs; reduced report load time 50%; Star Employee 2019 and 2020

### Hard Skills

| Category | Skills |
|---|---|
| Product Management | Roadmap ownership, backlog management (RICE/MoSCoW/WSJF), PRD writing, user stories + acceptance criteria, A/B testing, sprint ceremonies, UAT, go-to-market, PMF analysis |
| Data & AI | SQL (PostgreSQL, MS SQL), Python (pandas), Power BI, ML model deployment, GenAI/LLM, RAG, agent architectures (LangChain, AutoGen, Semantic Kernel) |
| Delivery | Agile/Scrum, Jira, OKR frameworks, release planning, stakeholder management, executive communication, requirements gathering, BPMN/Lucidchart/Miro |
| Domain | P&C Insurance, BFSI, Motor Claims, Fraud Intelligence, IRDAI compliance, OEM Integrations, Omnichannel, Digital Transformation |
| UX & Design | Figma, Balsamiq, user personas, journey mapping, UX research |

### Resume Variants

| Variant Name | Use When |
|---|---|
| `PM — BFSI` | PM/PO role at BFSI / FinTech / Insurance company or GCC |
| `PM — Non-BFSI` | PM/PO role at tech, SaaS, e-commerce, or non-financial company |
| `PM / Owner — Basic` | PM or PO role where domain is unclear or mixed |
| `Business Analyst` | BA, Senior BA, Lead BA, or BA Manager role |
| `Business Strategy` | Strategy, Analytics, Chief of Staff, Revenue/Growth roles |
| `Consulting` | Management Consulting, Digital Transformation, Strategy Consulting |
| `Program Manager` | Program Manager, Delivery Manager, Agile Coach, Scrum Master (senior) |
| `Project Management` | Project Manager, PMO, Technical PM roles |
| `Strategy Consultant` | Senior Consulting / Solution Architecture / Enterprise Advisory |

### Target Locations
- Hyderabad, Telangana (primary)
- Bengaluru, Karnataka (primary)

### Open Roles
1. Product Manager / Senior PM / Principal PM / Group PM
2. Product Owner / Senior PO
3. Business Analyst / Senior BA / BA Manager / Lead BA
4. Consultant / Strategy Consultant / Digital Transformation Consultant / Management Consultant

---

## Scoring Rubric

### Step 1 — Role Alignment (0–40 pts) · Title-based

| Condition | Points | Role Type |
|---|---|---|
| PM / Senior PM / Group PM / Principal PM / Lead PM / Staff PM | 40 | Product Manager |
| Product Owner / Senior PO | 37 | Product Owner |
| Business Analyst (Manager / Senior / Lead / Technical) | 35 | Business Analyst |
| Consultant / Strategy / Digital Transformation / Management Consultant | 33 | Consultant/Strategy |
| Adjacent role (Program Manager, Delivery Manager, BA-PM hybrid) | 28 | Program Manager |
| Weakly adjacent (Analytics Manager, Ops Manager, TPM) | 18 | — |
| No overlap (Engineering Manager, Sales, HR, SWE) | 0 | EXCLUDE |

### Step 2 — Skills Match (0–30 pts) · Description-based

| JD Signal | Points |
|---|---|
| Roadmap ownership / product strategy explicitly mentioned | +5 |
| AI / ML / GenAI product delivery or platform deployment | +5 |
| Backlog management / sprint ceremonies / Agile / Scrum | +4 |
| Requirements gathering / BRD / FRD / user stories / UAT | +4 |
| Cross-functional stakeholder management | +4 |
| Data analytics: SQL / Power BI / Python / dashboards / KPIs | +4 |
| Process improvement / automation / digital transformation | +4 |
| **Cap at 30 pts** | |

### Step 3 — Domain Bonus (0–20 pts) · Description-based

| Condition | Points |
|---|---|
| Insurance / P&C / Motor / Claims explicitly in JD | +10 |
| BFSI / FinTech / Payments / Banking in JD | +7 |
| HealthTech / RegTech / Risk / Compliance adjacent | +4 |
| MBA / IIM / Tier-1 MBA callout in JD | +5 |
| AI/ML/GenAI as primary product focus (not just tools) | +5 |
| **Cap at 20 pts** | |

### Step 4 — Company / Brand Bonus (0–10 pts)

| Condition | Points |
|---|---|
| Top-tier GCC: Amazon, Google, Microsoft, Salesforce, JPMorgan, Goldman Sachs, Wells Fargo, BlackRock | +10 |
| hackajob listing if JP Morgan/Goldman/top BFSI mentioned in JD | +10 |
| Strong GCC / MNC: EY, Deloitte, PwC, HSBC, Deutsche Bank, Synchrony, Nielsen, Autodesk, Franklin Templeton, Experian, Optum, SimCorp, NatWest, State Street, Broadridge, Wise | +7 |
| Reputed firm: Wipro, Infosys, TCS, Genpact, Capgemini, Accenture, Cognizant, CGI, Luxoft, Publicis Sapient, Endava | +4 |
| Startup with known brand / funded / InsurTech / FinTech | +3 |
| Unknown / recruiter-posted / no brand signal | +0 |
| **Cap at 10 pts** | |

### Thresholds
- Score ≥ 75 → **High** — include always
- Score 55–74 → **Medium** — include if needed to reach 30
- Score < 55 → **Exclude**

### Scoring rules — common mistakes to avoid
- Do NOT score high for purely engineering, sales, or HR roles — Step 1 = 0, exclude
- Do NOT award BFSI bonus if only tangentially mentioned in company description — JD must explicitly reference BFSI context
- DO award AI bonus ONLY if JD explicitly mentions building/deploying/owning AI/ML products — not just "work with AI teams"
- DO award MBA bonus only if JD says "MBA preferred" or "MBA from Tier-1 institute"
- DO cite specific JD phrases in Match Reason — e.g. "JD says 'own the product roadmap for AI claims platform'" not "role involves product management"

---

## Morning Digest Excel Spec (`output/jobs_YYYY-MM-DD.xlsx`)

**Sheet: "Scored Jobs"** — top 30 rows, sorted by Match Score descending

| # | Column | How to populate |
|---|---|---|
| A | **Role Type** | Product Manager / Product Owner / Business Analyst / Consultant/Strategy |
| B | **Job Title** | Exact title from listing |
| C | **Company** | Company name |
| D | **City** | Hyderabad or Bengaluru |
| E | **GCC?** | Yes if confirmed MNC India GCC; No otherwise |
| F | **Source** | LinkedIn / Glassdoor / Naukri / Indeed |
| G | **Salary (INR)** | From scraper metadata — "Not Listed" if unavailable |
| H | **Experience Range** | e.g. "5-8 yrs" — "Not Listed" if unavailable |
| I | **Posted Date** | YYYY-MM-DD |
| J | **Posted (Hrs Ago)** | Calculated at time of run |
| K | **Match Score** | 0–100 per rubric |
| L | **Match Reason** | 2–3 lines citing SPECIFIC JD phrases. Reference Pranav's achievements where relevant. Flag ⚡ if posted by named individual |
| M | **Interview Likelihood** | High (score ≥75 + strong domain fit) / Medium / Low |
| N | **Best Resume Variant** | From Resume Variants table above |
| O | **Apply Link** | Direct URL — hyperlinked |
| P | **Job ID** | Platform Job ID from URL or scraper |
| Q | **Recruiter / Poster LinkedIn** | `linkedin.com/in/...` only — "Not Available" if not found |
| R | **Employees Search Link** | `https://www.linkedin.com/search/results/people/?keywords=%22[Company]%22` |
| S | **Job Description** | Full JD if enriched via get_job_details; otherwise first 2000 chars from JobSpy |

### Formatting

**Header row (Row 1)**
- Fill: `#1F3864` (dark navy) · Font: white, bold, size 9 · Height: 30px · Center-aligned, wrap text

**Data rows (Rows 2–31)**
- Height: 65px · Font: size 9, wrap text · Only specific cells coloured (NOT full row):

| Column | Fill logic |
|---|---|
| A — Role Type | `#C6D9F1` blue=PM · `#FFE699` amber=PO · `#FCE4D6` peach=BA · `#E2CBFF` lilac=Consultant |
| F — Source | `#D9C3F0` purple=Indeed · `#BDD7EE` blue=LinkedIn · `#F4B942` orange=Naukri · `#C6EFCE` green=Glassdoor |
| K — Match Score | `#C6EFCE` green ≥75 · `#FFEB9C` amber 55–74 · `#FFC7CE` red <55 |
| M — Interview Likelihood | `#C6EFCE` green=High · `#FFEB9C` amber=Medium · `#FFC7CE` red=Low |

**Column widths:** A=18, B=45, C=28, D=13, E=7, F=9, G=16, H=16, I=13, J=13, K=12, L=75, M=18, N=18, O=38, P=15, Q=20, R=40, S=80

**Other:** Freeze Row 1 · Auto-filter Row 1 · Sort by Match Score descending

### Legend Sheet (6 sections)

1. **RUN METADATA** — Run Date, Cities, Search Terms, Source breakdown, Filter note, Rows included/excluded
2. **COLOUR GUIDE** — Role / Score / Source colour key
3. **SCORING RUBRIC SUMMARY** — Steps 1–4 condensed
4. **TOP 5 PICKS** — with one-line specific reason referencing JD language
5. **⭐ FRESH TODAY** — jobs posted on run_date only
6. **⚠️ NOTES** — anomalies, overqualification flags, stale postings

---

## Hard Rules

- Match Reason MUST cite specific words/phrases from the JD — not generic descriptions
- Only `linkedin.com/in/...` personal profiles in Recruiter column — never company pages
- Never fabricate Job IDs, apply links, or LinkedIn profiles
- Salary and Experience Range from scraper metadata only — "Not Listed" if unavailable
- All 30 rows fully populated
- GCC = Yes only for confirmed MNC India offices / Global Capability Centres
- Do NOT award BFSI/insurance domain bonus if the domain only appears in company boilerplate — it must appear in the JD body
- Interview Likelihood = High only when score ≥75 AND JD domain clearly matches Pranav's insurance/BFSI/AI PM background

---

## What GitHub Actions Does (you don't need to do this)

After `git push`:
- Push to `output/jobs_*.xlsx` → `send_to_telegram.yml` fires → sends Excel + interactive cards to Telegram
- Push to `output/apply_*.xlsx` → `send_apply_list.yml` fires → sends apply-list Excel to Telegram
- `bot_poll.yml` runs every 15 min → handles ✅/❌ taps, URL pastes, `/apply`, `/status`
