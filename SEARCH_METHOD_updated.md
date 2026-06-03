# UPDATED SEARCH METHOD — replaces existing SEARCH METHOD block in master prompt
# Drop-in replacement. All other sections (profile, scoring, Excel spec) unchanged.

---

## SEARCH METHOD

### TIER 1 — Primary (GitHub Actions · JobSpy · $0)

Fetch today's pre-scraped jobs from the GitHub repo using WebFetch:

    URL: https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/pranav-job-search/main/jobs_raw.json

The JSON contains:
- `run_date` — date the scrape ran (YYYY-MM-DD)
- `total_jobs` — number of unique deduplicated listings
- `jobs[]` — array of job objects with fields:

| Field | Source | Notes |
|---|---|---|
| title | All | Job title |
| company | All | Company name |
| location | All | City/state/country object or string |
| site | All | linkedin / naukri / indeed / glassdoor |
| job_url | All | Direct apply link |
| date_posted | All | ISO date string |
| description | All | Markdown (LinkedIn full JD; others partial) |
| min_amount / max_amount | Where available | Salary figures |
| currency / interval | Where available | INR / yearly etc. |
| experience_range | Naukri | e.g. "5-8 Yrs" |
| skills | Naukri | List of required skills |
| job_level | LinkedIn | e.g. "Senior", "Mid-Senior" |
| company_rating | Naukri | AmbitionBox rating |
| _search_term | Internal | Which keyword found this job |
| _search_location | Internal | Hyderabad or Bangalore |

After fetching:
1. Parse `jobs[]` array
2. Filter: keep only jobs where `date_posted` is within last 24 hours of `run_date`
   (scraper uses 48h window to catch timezone lag; apply the 24h filter here)
3. Deduplicate by title + company if any remain (should already be done)
4. Proceed to scoring

### TIER 2 — Supplementary (Indeed MCP · free)

Run in parallel with Tier 1 fetch, 5 queries:

    mcp__Indeed__search_jobs, country_code=IN:
    1. search="Product Manager AI"             location="Hyderabad"
    2. search="Senior Product Manager"          location="Bangalore"
    3. search="Strategy Consultant BFSI"        location="Hyderabad"
    4. search="Consultant Digital Transformation" location="Bangalore"
    5. search="Business Analyst Insurance"      location="Hyderabad"

For top-10 Indeed candidates by title-based score, call mcp__Indeed__get_job_details
to retrieve full JD before finalising Match Reason.

### SKIP
- ❌ All Apify actors — replaced by GitHub Actions + JobSpy ($0/day)
- ❌ Dice / ZipRecruiter — US-only

### Deduplication
- Deduplicate Tier 1 + Tier 2 by Job Title + Company
- Source preference: LinkedIn > Glassdoor > Naukri > Indeed
- Discard anything where date_posted > 24 hours before time of run
