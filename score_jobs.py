"""
Scores jobs_raw.json and saves data/today_jobs.json + resets daily state files.
No Telegram calls. Run this BEFORE sending cards so bot_poll always finds the index.
"""
import json
from datetime import date, timedelta
from pathlib import Path

JSON_PATH = "jobs_raw.json"


def role_score(t):
    t = t.lower()
    for kw in ["principal product manager","senior product manager","lead product manager",
                "staff product manager","product manager, senior"]:
        if kw in t: return 40, "Product Manager"
    if "product manager" in t:   return 40, "Product Manager"
    if "product owner" in t:     return 37, "Product Owner"
    for kw in ["senior business analyst","lead business analyst","technical business analyst"]:
        if kw in t: return 35, "Business Analyst"
    if "business analyst" in t:  return 35, "Business Analyst"
    for kw in ["consultant, strategy","strategy, growth","transformation consultant",
                "management consultant","digital transformation","strategy consultant"]:
        if kw in t: return 33, "Consultant/Strategy"
    if "consultant" in t:        return 33, "Consultant/Strategy"
    for kw in ["program manager","delivery manager","project manager"]:
        if kw in t: return 28, "Program Manager"
    for kw in ["product specialist","product analyst","product associate","product operations"]:
        if kw in t: return 28, "Product Manager"
    return 0, None

def skills_pts(d):
    if not d: return 0
    d = d.lower(); p = 0
    if "roadmap" in d or "product strategy" in d:          p += 5
    if any(x in d for x in ["backlog","sprint","agile","scrum"]): p += 4
    if any(x in d for x in ["requirements","acceptance criteria","uat"]): p += 4
    if "stakeholder" in d:                                  p += 4
    if any(x in d for x in ["sql","power bi","kpi","analytics"]): p += 4
    if any(x in d for x in ["generative ai","machine learning","llm","agentic","ai/ml","ai product","ai-powered"]): p += 5
    if any(x in d for x in ["digital transformation","process improvement","automation"]): p += 4
    return min(p, 30)

def domain_pts(d):
    if not d: return 0
    d = d.lower(); p = 0
    if any(x in d for x in ["insurance","motor claims","claims"]):     p += 10
    elif any(x in d for x in ["bfsi","fintech","financial services","banking","payments"]): p += 7
    elif any(x in d for x in ["regtech","risk management","compliance"]): p += 4
    if any(x in d for x in ["mba or relevant advanced degree is a must","mba or another advanced degree","mba preferred"]): p += 5
    if any(x in d for x in ["ai product","generative ai","agentic","ai platform","ai strategy"]): p += 5
    return min(p, 20)

def brand_pts(c, d=""):
    c = (c or "").lower(); d = (d or "").lower()
    if any(x in c for x in ["amazon","google","microsoft","salesforce","jpmorgan","goldman","wells fargo","blackrock"]): return 10
    if "hackajob" in c and "jp morgan" in d: return 10
    if any(x in c for x in ["deloitte","pwc","hsbc","synchrony","nielsen","experian","optum","simcorp","natwest","state street","broadridge","wise"]): return 7
    if any(x in c for x in ["wipro","infosys","tcs","genpact","capgemini","accenture","cognizant","publicis sapient","endava"]): return 4
    return 0

def salary_str(j):
    lo = j.get("min_amount"); hi = j.get("max_amount"); cur = j.get("currency") or ""
    if lo and hi:  return f"{cur}{int(lo):,}–{int(hi):,}"
    if lo:         return f"{cur}{int(lo):,}+"
    return ""


with open(JSON_PATH) as f:
    raw = json.load(f)

run_date_str = raw.get("run_date", str(date.today()))
try:
    run_date = date.fromisoformat(run_date_str)
except ValueError:
    run_date = date.today()
cutoff = (run_date - timedelta(hours=48)).isoformat()

scored = []; seen = set()
for j in raw.get("jobs", []):
    dp = j.get("date_posted"); title = j.get("title","") or ""; company = j.get("company","") or ""
    desc = j.get("description","") or ""
    if dp and dp < cutoff: continue
    r1, rt = role_score(title)
    if r1 == 0: continue
    key = (company.lower()[:20], title.lower()[:35])
    if key in seen: continue
    seen.add(key)
    total = r1 + skills_pts(desc) + domain_pts(desc) + brand_pts(company, desc)
    if total < 55: continue
    scored.append({"score":total,"title":title,"company":company,"url":j.get("job_url","") or "",
                    "date":dp or "Recent","role":rt or "","location":j.get("location","") or "",
                    "salary":salary_str(j),"site":j.get("site","") or ""})

scored.sort(key=lambda x: -x["score"])
for i, j in enumerate(scored): j["idx"] = i

Path("data").mkdir(exist_ok=True)

with open("data/today_jobs.json", "w") as f:
    json.dump({"date": run_date_str, "jobs": scored}, f, indent=2)

for path, template in [
    ("data/shortlisted.json", {"date": run_date_str, "jobs": []}),
    ("data/manual_jobs.json", {"date": run_date_str, "entries": []}),
]:
    p = Path(path)
    existing = {}
    if p.exists():
        try: existing = json.loads(p.read_text())
        except: pass
    if existing.get("date") != run_date_str:
        with open(path, "w") as f:
            json.dump(template, f, indent=2)

print(f"Scored {len(scored)} jobs for {run_date_str}. Saved to data/today_jobs.json.")
