"""
Telegram notifier for Pranav's daily job search.
Reads jobs_raw.json, scores top jobs, sends a digest to Telegram.

Usage (local):
    TELEGRAM_TOKEN=xxx TELEGRAM_CHAT_ID=yyy python3 telegram_notify.py

Usage (GitHub Actions):  set TELEGRAM_TOKEN + TELEGRAM_CHAT_ID as repo secrets.
"""

import json
import os
import sys
import urllib.request
from datetime import date

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
JSON_PATH = os.environ.get("JOBS_JSON", "jobs_raw.json")

if not TOKEN or not CHAT_ID:
    sys.exit("ERROR: set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID environment variables.")


# ── scoring (mirrors generate_excel.py) ──────────────────────────────────────

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
    if "roadmap" in d or "product strategy" in d:      p += 5
    if any(x in d for x in ["backlog", "sprint", "agile", "scrum"]): p += 4
    if any(x in d for x in ["requirements", "acceptance criteria", "uat"]): p += 4
    if "stakeholder" in d:                             p += 4
    if any(x in d for x in ["sql", "power bi", "kpi", "analytics"]): p += 4
    if any(x in d for x in ["generative ai", "machine learning", "llm",
                              "agentic", "ai/ml", "ai product", "ai-powered"]): p += 5
    if any(x in d for x in ["digital transformation", "process improvement",
                              "automation"]):           p += 4
    return min(p, 30)

def domain_pts(d):
    if not d: return 0
    d = d.lower(); p = 0
    if any(x in d for x in ["insurance", "motor claims", "claims"]):      p += 10
    elif any(x in d for x in ["bfsi", "fintech", "financial services",
                                "banking", "payments"]):                   p += 7
    elif any(x in d for x in ["regtech", "risk management", "compliance"]): p += 4
    if any(x in d for x in ["mba or relevant advanced degree is a must",
                              "mba or another advanced degree",
                              "mba preferred"]):                           p += 5
    if any(x in d for x in ["ai product", "generative ai", "agentic",
                              "ai platform", "ai strategy"]):              p += 5
    return min(p, 20)

def brand_pts(c):
    c = (c or "").lower()
    if any(x in c for x in ["amazon","google","microsoft","salesforce",
                              "jpmorgan","jp morgan","goldman","wells fargo","blackrock"]):
        return 10
    if any(x in c for x in ["deloitte","pwc","hsbc","synchrony","nielsen","experian",
                              "optum","simcorp","natwest","state street","broadridge","wise"]):
        return 7
    if any(x in c for x in ["wipro","infosys","tcs","genpact","capgemini","accenture",
                              "cognizant","publicis sapient","endava"]):
        return 4
    return 0

def score_job(j):
    title   = j.get("title", "") or ""
    company = j.get("company", "") or ""
    desc    = j.get("description", "") or ""
    r1, rt  = role_score(title)
    if r1 == 0:
        return None
    r4 = brand_pts(company)
    if "hackajob" in company.lower() and "jp morgan" in desc.lower():
        r4 = 10
    total = r1 + skills_pts(desc) + domain_pts(desc) + r4
    return total if total >= 55 else None


# ── load + score ──────────────────────────────────────────────────────────────

with open(JSON_PATH) as f:
    data = json.load(f)

run_date = data.get("run_date", str(date.today()))
jobs_raw = data.get("jobs", [])

scored = []
seen   = set()

for j in jobs_raw:
    dp = j.get("date_posted")
    if dp and dp < "2026-06-01":   # 48h filter relative to run_date
        continue
    title   = j.get("title", "") or ""
    company = j.get("company", "") or ""
    key     = (company.lower()[:20], title.lower()[:35])
    if key in seen:
        continue
    total = score_job(j)
    if total is None:
        continue
    seen.add(key)
    scored.append((total, j))

scored.sort(key=lambda x: -x[0])
top = scored[:10]   # send top 10 in Telegram


# ── format message ────────────────────────────────────────────────────────────

ROLE_EMOJI = {
    "Product Manager":    "🧩",
    "Product Owner":      "📋",
    "Business Analyst":   "📊",
    "Consultant/Strategy":"💼",
    "Program Manager":    "🗂",
}

def il_emoji(s):
    if s >= 75: return "🟢"
    if s >= 60: return "🟡"
    return "🔴"

lines = [
    f"<b>📌 Pranav's Job Digest — {run_date}</b>",
    f"<i>Run date: {run_date} · Top {len(top)} of {len(scored)} qualifying roles</i>",
    "",
]

for rank, (sc, j) in enumerate(top, 1):
    title   = j.get("title", "")
    company = j.get("company", "")
    url     = j.get("job_url", "")
    dp      = j.get("date_posted") or "Recent"
    r1, rt  = role_score(title)
    emoji   = ROLE_EMOJI.get(rt, "🔹")
    tag     = f"[{rt}]" if rt else ""

    line = (
        f"{il_emoji(sc)} <b>#{rank} · {sc}/100</b> {emoji} {tag}\n"
        f"<b>{title}</b>\n"
        f"🏢 {company} · 📅 {dp}\n"
    )
    if url:
        line += f'<a href="{url}">Apply →</a>'
    lines.append(line)
    lines.append("")

lines.append("━━━━━━━━━━━━━━━━━━━━")
lines.append("Full sheet: check your daily Excel file.")
lines.append(f"<i>High ≥75 🟢 | Medium 55–74 🟡</i>")

message = "\n".join(lines)


# ── send ──────────────────────────────────────────────────────────────────────

def send(text):
    url     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# Telegram limit = 4096 chars; split if needed
MAX = 4000
chunks = [message[i:i+MAX] for i in range(0, len(message), MAX)]
for chunk in chunks:
    result = send(chunk)
    if not result.get("ok"):
        sys.exit(f"Telegram error: {result}")

print(f"✅ Sent {len(chunks)} message(s) to Telegram. Top {len(top)} jobs delivered.")
