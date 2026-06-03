# Pranav Job Search — GitHub Actions Bridge

Daily job scraper using [JobSpy](https://github.com/speedyapply/JobSpy).  
Runs at **8:00 AM IST** every day. Results written to `jobs_raw.json`.  
Claude Code fetches the JSON via WebFetch (GitHub raw URLs are always allowed).

## One-Time Setup

### 1. Create the GitHub repository

```bash
# From this directory
git init
git add .
git commit -m "init: job search setup"
gh repo create pranav-job-search --public --push --source=.
```

> Can be private too — but then you need to generate a fine-grained PAT with
> `contents: read` and add it as `GITHUB_TOKEN` override. Public is simpler.

### 2. Enable GitHub Actions

Go to your repo → **Actions** tab → click **"I understand my workflows, go ahead and enable them"**

### 3. Update the master prompt

Replace `YOUR_GITHUB_USERNAME` in `SEARCH_METHOD_updated.md` with your actual GitHub username, then paste the full updated block into your Claude Code daily job search trigger prompt.

### 4. Test it

Trigger a manual run:
```
GitHub → Actions → Daily Job Search → Run workflow
```
Check the run logs. After it succeeds, verify `jobs_raw.json` is committed to the repo.

### 5. Verify Claude can fetch it

The URL Claude will WebFetch daily:
```
https://raw.githubusercontent.com/YOUR_USERNAME/pranav-job-search/main/jobs_raw.json
```

## Files

| File | Purpose |
|---|---|
| `jobspy_run.py` | JobSpy scraper — runs on GitHub Actions |
| `.github/workflows/daily_job_search.yml` | Cron schedule (8am IST daily) |
| `jobs_raw.json` | Output file — auto-committed after each run |
| `SEARCH_METHOD_updated.md` | Drop-in replacement for the SEARCH METHOD block in your master prompt |

## Adjusting the scraper

Edit `jobspy_run.py`:
- `RESULTS_PER_SITE` — jobs per site per search term (default 15)
- `HOURS_OLD` — recency filter (default 48; Claude applies 24h filter after fetch)
- `DESC_MAX_CHARS` — description truncation (default 2500)
- `SEARCHES` — add/remove search terms or cities

## Cost

| Component | Cost |
|---|---|
| GitHub Actions | Free (2000 min/month on free tier; this job takes ~2–3 min/day) |
| JobSpy library | Free, open-source |
| Claude Code WebFetch | Covered by Claude token budget (user confirmed this is fine) |
| **Total** | **$0.00/day** |
