"""
Telegram notifier for Pranav's daily job search.
Reads jobs_raw.json, scores top jobs, sends a digest to Telegram.

Usage (local):
    TELEGRAM_TOKEN=xxx TELEGRAM_CHAT_ID=yyy python3 telegram_notify.py

Usage (GitHub Actions): set TELEGRAM_TOKEN + TELEGRAM_CHAT_ID as repo secrets.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta

TOKEN     = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
JSON_PATH = os.environ.get("JOBS_JSON", "jobs_raw.json")

if not TOKEN or not CHAT_ID:
    print("WARNING: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set — skipping Telegram notification.")
    sys.exit(0)   # exit 0 so the workflow commit step still runs


# ── scoring ───────────────────────────────────────────────────────────────────

def role_score(t):
    t = t.lower()
    if any(x in t for x in ["principal product manager", "senior product manager",
                              "lead product manager", "staff product manager",
                              "product manager, senior"]):
        return 40, "Product Manager"
    if "product manager" in t:   return 40, "Product Manager"
    if "product owner" in t:     return 37, "Product Owner"
    if any(x in t for x in ["senior business analyst", "lead business analyst",
                              "technical business analyst"]):
        return 35, "Business Analyst"
    if "business analyst" in t:  return 35, "Business Analyst"
    if any(x in t for x in ["consultant, strategy", "strategy, growth",
                              "transformation consultant", "management consultant",
                              "digital transformation", "strategy consultant"]):
        return 33, "Consultant/Strategy"
    if "consultant" in t:        return 33, "Consultant/Strategy"
    if any(x in t for x in ["program manager", "delivery manager", "project manager"]):
        return 28, "Program Manager"
    if any(x in t for x in ["product specialist", "product analyst",
                              "product associate", "product operations"]):
        return 28, "Product Manager"
    return 0, None

def skills_pts(d):
    if not d: return 0
    d = d.lower(); p = 0
    if "roadmap" in d or "product strategy" in d:          p += 5
    if any(x in d for x in ["backlog", "sprint", "agile", "scrum"]): p += 4
    if any(x in d for x in ["requirements", "acceptance criteria", "uat"]): p += 4
    if "stakeholder" in d:                                  p += 4
    if any(x in d for x in ["sql", "power bi", "kpi", "analytics"]): p += 4
    if any(x in d for x in ["generative ai", "machine learning", "llm",
                              "agentic", "ai/ml", "ai product", "ai-powered"]): p += 5
    if any(x in d for x in ["digital transformation", "process improvement",
                              "automation"]):               p += 4
    return min(p, 30)

def domain_pts(d):
    if not d: return 0
    d = d.lower(); p = 0
    if any(x in d for x in ["insurance", "motor claims", "claims"]):     p += 10
    elif any(x in d for x in ["bfsi", "fintech", "financial services",
                                "banking", "payments"]):                  p += 7
    elif any(x in d for x in ["regtech", "risk management", "compliance"]): p += 4
    if any(x in d for x in ["mba or relevant advanced degree is a must",
                              "mba or another advanced degree",
                              "mba preferred"]):                          p += 5
    if any(x in d for x in ["ai product", "generative ai", "agentic",
                              "ai platform", "ai strategy"]):             p += 5
    return min(p, 20)

def brand_pts(c, d=""):
    c = (c or "").lower(); d = (d or "").lower()
    if any(x in c for x in ["amazon","google","microsoft","salesforce","jpmorgan",
                              "goldman","wells fargo","blackrock"]):         return 10
    if "hackajob" in c and "jp morgan" in d:                                return 10
    if any(x in c for x in ["deloitte","pwc","hsbc","synchrony","nielsen",
                              "experian","optum","simcorp","natwest",
                              "state street","broadridge","wise"]):          return 7
    if any(x in c for x in ["wipro","infosys","tcs","genpact","capgemini",
                              "accenture","cognizant","publicis sapient",
                              "endava"]):                                     return 4
    return 0


# ── load & score ──────────────────────────────────────────────────────────────

try:
    with open(JSON_PATH) as f:
        data = json.load(f)
except Exception as e:
    print(f"ERROR reading {JSON_PATH}: {e}")
    sys.exit(0)   # don't block commit step

run_date_str = data.get("run_date", str(date.today()))
try:
    run_date = date.fromisoformat(run_date_str)
except ValueError:
    run_date = date.today()

cutoff = (run_date - timedelta(hours=48)).isoformat()   # dynamic, not hardcoded
jobs_raw = data.get("jobs", [])

scored = []
seen   = set()

for j in jobs_raw:
    dp      = j.get("date_posted")
    title   = j.get("title", "") or ""
    company = j.get("company", "") or ""
    desc    = j.get("description", "") or ""

    # Date filter: keep null (LinkedIn recent) or within 48h of run_date
    if dp and dp < cutoff:
        continue

    r1, rt = role_score(title)
    if r1 == 0:
        continue

    key = (company.lower()[:20], title.lower()[:35])
    if key in seen:
        continue
    seen.add(key)

    total = r1 + skills_pts(desc) + domain_pts(desc) + brand_pts(company, desc)
    if total < 55:
        continue

    scored.append((total, title, company, j.get("job_url", ""), dp or "Recent", rt))

scored.sort(key=lambda x: -x[0])
top = scored[:10]


# ── format ────────────────────────────────────────────────────────────────────

ROLE_EMOJI = {
    "Product Manager":     "🧩",
    "Product Owner":       "📋",
    "Business Analyst":    "📊",
    "Consultant/Strategy": "💼",
    "Program Manager":     "🗂",
}

def score_dot(s):
    return "🟢" if s >= 75 else ("🟡" if s >= 60 else "🔴")

lines = [
    f"<b>📌 Pranav's Job Digest — {run_date_str}</b>",
    f"<i>{len(top)} of {len(scored)} qualifying roles · High ≥75🟢 Med 55–74🟡</i>",
    "",
]

for rank, (sc, title, company, url, dp, rt) in enumerate(top, 1):
    emoji = ROLE_EMOJI.get(rt, "🔹")
    line  = f"{score_dot(sc)} <b>#{rank} · {sc}/100</b> {emoji} <b>{title}</b>\n🏢 {company} · 📅 {dp}"
    if url:
        line += f'\n<a href="{url}">Apply →</a>'
    lines += [line, ""]

lines += ["━━━━━━━━━━━━━━━━━━━━", "<i>Full Excel sheet generated in repo artifacts.</i>"]
message = "\n".join(lines)


# ── send ──────────────────────────────────────────────────────────────────────

def send(text):
    url     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id":                  CHAT_ID,
        "text":                     text,
        "parse_mode":               "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

MAX    = 4000
chunks = [message[i:i+MAX] for i in range(0, len(message), MAX)]

for i, chunk in enumerate(chunks, 1):
    try:
        result = send(chunk)
        if result.get("ok"):
            print(f"✅ Telegram message {i}/{len(chunks)} sent.")
        else:
            print(f"WARNING: Telegram returned not-ok: {result}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"WARNING: Telegram HTTP {e.code}: {body}")
    except Exception as e:
        print(f"WARNING: Telegram send failed: {e}")

# Always exit 0 — Telegram failure must never block the commit step
print(f"Done. {len(top)} jobs processed from {run_date_str}.")
sys.exit(0)
