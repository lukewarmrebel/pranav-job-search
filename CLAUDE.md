# Pranav Job Search — Claude Routines

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

2. **Read scraped jobs**
   - Read `jobs_raw.json` from the local repo (already pulled)
   - Note `run_date` from the JSON header
   - Filter: keep only jobs where `date_posted` is within last 24h of `run_date` OR null
   - Deduplicate by title + company

3. **Run Indeed MCP enrichment (Tier 2) in parallel**
   ```
   mcp__Indeed__search_jobs, country_code=IN:
     1. search="Product Manager AI"               location="Hyderabad"
     2. search="Senior Product Manager"            location="Bangalore"
     3. search="Strategy Consultant BFSI"          location="Hyderabad"
     4. search="Consultant Digital Transformation" location="Bangalore"
     5. search="Business Analyst Insurance"        location="Hyderabad"
   ```
   For top-10 Indeed candidates by title score, call `mcp__Indeed__get_job_details` for full JD.
   Deduplicate Tier 1 + Tier 2 combined by title + company.
   Source preference for duplicates: LinkedIn > Glassdoor > Naukri > Indeed.

4. **Score every job** using the rubric below. Skip anything scoring < 55.

5. **Generate Excel** → save to `output/jobs_YYYY-MM-DD.xlsx`
   Use the Excel spec below. Top 30 rows by score.

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
       },
       ...all scored jobs, sorted by score desc, idx 0-based...
     ]
   }
   ```

7. **Reset daily state files** (new day, clear yesterday's shortlist)
   Write `data/shortlisted.json`: `{"date": "YYYY-MM-DD", "jobs": []}`
   Write `data/skipped.json`:     `{"date": "YYYY-MM-DD", "jobs": []}`
   Write `data/manual_jobs.json`: `{"date": "YYYY-MM-DD", "entries": []}`

8. **Commit and push** → this triggers GitHub Actions to send to Telegram automatically
   ```bash
   git add output/jobs_YYYY-MM-DD.xlsx data/today_jobs.json \
           data/shortlisted.json data/skipped.json data/manual_jobs.json
   git commit -m "digest: job search YYYY-MM-DD"
   git pull origin master --rebase
   git push
   ```

9. **Send Excel to user in chat as well** via SendUserFile tool (for immediate reference)

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
   - All scored jobs from today_jobs.json with Decision column:
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

6. **Send Excel to user in chat as well** via SendUserFile tool

---

## Scoring Rubric

### Step 1 — Role Alignment (max 40 pts) · Title-based

| Title contains | Score | Role Type |
|---|---|---|
| principal/senior/lead/staff product manager, "product manager, senior" | 40 | Product Manager |
| product manager | 40 | Product Manager |
| product owner | 37 | Product Owner |
| senior/lead/technical business analyst | 35 | Business Analyst |
| business analyst | 35 | Business Analyst |
| consultant (strategy/growth/transformation/management/digital/strategy) | 33 | Consultant/Strategy |
| consultant | 33 | Consultant/Strategy |
| program manager / delivery manager / project manager | 28 | Program Manager |
| product specialist / analyst / associate / operations | 28 | Product Manager |
| anything else | 0 | skip entirely |

### Step 2 — Skills Match (max 30 pts) · Description-based

| Keyword in description | Points |
|---|---|
| roadmap OR product strategy | +5 |
| generative ai / machine learning / llm / agentic / ai/ml / ai product / ai-powered | +5 |
| backlog / sprint / agile / scrum | +4 |
| requirements / acceptance criteria / uat | +4 |
| stakeholder | +4 |
| sql / power bi / kpi / analytics | +4 |
| digital transformation / process improvement / automation | +4 |

Cap at 30.

### Step 3 — Domain Bonus (max 20 pts) · Description-based

| Keyword | Points |
|---|---|
| insurance / motor claims / claims | +10 |
| bfsi / fintech / financial services / banking / payments | +7 |
| regtech / risk management / compliance | +4 |
| mba required/preferred phrases | +5 |
| ai product / generative ai / agentic / ai platform / ai strategy | +5 |

Cap at 20.

### Step 4 — Company Brand (max 10 pts)

| Company | Points |
|---|---|
| Amazon, Google, Microsoft, Salesforce, JPMorgan, Goldman Sachs, Wells Fargo, BlackRock | 10 |
| hackajob listing if JP Morgan mentioned in JD | 10 |
| Deloitte, PwC, HSBC, Synchrony, Nielsen, Experian, Optum, SimCorp, NatWest, State Street, Broadridge, Wise | 7 |
| Wipro, Infosys, TCS, Genpact, Capgemini, Accenture, Cognizant, Publicis Sapient, Endava | 4 |

### Threshold
Total < 55 → exclude from output entirely.
🟢 ≥ 75 · 🟡 60–74 · 🔴 55–59

---

## Morning Digest Excel Spec (`output/jobs_YYYY-MM-DD.xlsx`)

**Sheet: "Scored Jobs"** — top 30 rows, sorted by score desc

| Col | Header | Source |
|---|---|---|
| A | # | rank |
| B | Score | total score |
| C | Role Type | Product Manager / Business Analyst / etc |
| D | Title | job title |
| E | Company | company name |
| F | Location | city |
| G | Date Posted | date_posted |
| H | Salary | min–max if available |
| I | Site | linkedin / naukri / indeed |
| J | Apply URL | hyperlinked |
| K | Match Reason | Claude's 1-sentence reasoning why this fits Pranav |
| L | Experience | experience_range if available |
| M | Job Level | job_level if available |
| N | Key Skills | top 5 skills from description |

**Formatting:**
- Header row: dark blue (#1F4E79), white bold text
- 🟢 Score ≥ 75: green fill (#E2EFDA)
- 🟡 Score 60–74: yellow fill (#FFEB9C)
- 🔴 Score 55–59: red fill (#FFC7CE)
- Column J (Apply URL): hyperlink, blue underline
- Freeze row 1, auto-filter on all columns
- Sheet 2: "Legend" with colour key

---

## Pranav's Profile (for Match Reason column)

- **Target roles:** Senior/Lead Product Manager, Product Owner, Business Analyst, Strategy/Management Consultant
- **Domain strength:** Insurance (motor claims), BFSI, Fintech, Payments, RegTech
- **Skills:** Product roadmaps, stakeholder management, agile delivery, data analytics (SQL/Power BI), AI product management
- **Preferred:** Hyderabad or Bangalore · MBA holder · Open to top consulting firms and MNCs
- **Priority:** AI/ML product roles, insurance-tech, BFSI digital transformation

---

## What GitHub Actions Does (you don't need to do this)

After `git push`:
- Push to `output/jobs_*.xlsx` → `send_to_telegram.yml` fires → sends Excel + interactive cards to Telegram
- Push to `output/apply_*.xlsx` → `send_apply_list.yml` fires → sends apply-list Excel to Telegram
- `bot_poll.yml` runs every 15 min → handles ✅/❌ taps, URL pastes, `/apply`, `/status`
