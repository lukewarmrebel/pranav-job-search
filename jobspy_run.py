"""
Daily job scraper for Pranav Thatavarthi's job search.
Runs via GitHub Actions. Output: jobs_raw.json
"""
from jobspy import scrape_jobs
import pandas as pd
import json
from datetime import datetime, timezone, timedelta

SEARCHES = [
    ("Product Manager",  "Hyderabad, India"),
    ("Product Owner",    "Hyderabad, India"),
    ("Business Analyst", "Hyderabad, India"),
    ("Product Manager",  "Bangalore, India"),
    ("Product Owner",    "Bangalore, India"),
    ("Business Analyst", "Bangalore, India"),
]

SITES = ["linkedin", "naukri", "indeed", "glassdoor"]
RESULTS_PER_SITE = 15   # × 4 sites × 6 searches = up to 360 raw rows
HOURS_OLD = 48          # 48h catches timezone lag; Claude filters to 24h after
DESC_MAX_CHARS = 2500   # keep JSON file size manageable


def safe_val(v):
    """Make any value JSON-safe."""
    if v is None:
        return None
    if isinstance(v, float) and (v != v):  # NaN check
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    if isinstance(v, (list, dict)):
        return v
    return str(v) if not isinstance(v, (int, float, bool, str)) else v


def scrape(term, loc):
    try:
        df = scrape_jobs(
            site_name=SITES,
            search_term=term,
            location=loc,
            results_wanted=RESULTS_PER_SITE,
            hours_old=HOURS_OLD,
            country_indeed="india",
            linkedin_fetch_description=True,
            description_format="markdown",
            job_type="fulltime",
            verbose=0,
        )
        print(f"  [{term} | {loc}] → {len(df)} rows from {df['site'].value_counts().to_dict() if not df.empty else {}}")
        return df
    except Exception as e:
        print(f"  [{term} | {loc}] ERROR: {e}")
        return pd.DataFrame()


def main():
    print(f"=== JobSpy run: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} ===\n")

    frames = []
    for term, loc in SEARCHES:
        df = scrape(term, loc)
        if not df.empty:
            df["_search_term"] = term
            df["_search_location"] = loc
            frames.append(df)

    if not frames:
        print("No results — exiting.")
        return

    combined = pd.concat(frames, ignore_index=True)

    # Deduplicate by title + company (case-insensitive)
    combined["_dedup_key"] = (
        combined["title"].str.lower().str.strip() + "|" +
        combined["company"].str.lower().str.strip()
    )
    combined = combined.drop_duplicates(subset=["_dedup_key"]).drop(columns=["_dedup_key"])

    # Trim descriptions
    if "description" in combined.columns:
        combined["description"] = combined["description"].apply(
            lambda x: (str(x)[:DESC_MAX_CHARS] + "…") if pd.notna(x) and len(str(x)) > DESC_MAX_CHARS else x
        )

    # Build JSON-safe records
    records = []
    for _, row in combined.iterrows():
        records.append({k: safe_val(v) for k, v in row.items()})

    output = {
        "run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "cutoff_hours": HOURS_OLD,
        "total_jobs": len(records),
        "sites_searched": SITES,
        "searches_run": [{"term": t, "location": l} for t, l in SEARCHES],
        "jobs": records,
    }

    with open("jobs_raw.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n✓ Saved {len(records)} unique jobs to jobs_raw.json")

    # Quick breakdown
    df_out = pd.DataFrame(records)
    if not df_out.empty and "site" in df_out.columns:
        print("\nBy site:")
        print(df_out["site"].value_counts().to_string())
        print("\nBy location:")
        print(df_out["_search_location"].value_counts().to_string())


if __name__ == "__main__":
    main()
