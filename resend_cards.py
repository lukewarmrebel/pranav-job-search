"""
Resends today's interactive job cards to Telegram without re-scraping.
Reads data/today_jobs.json (or falls back to jobs_raw.json).
"""
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not TOKEN or not CHAT_ID:
    print("WARNING: no credentials — skipping.")
    sys.exit(0)


def tg_api(method, payload):
    url  = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"WARNING: {method} HTTP {e.code}: {e.read().decode(errors='replace')}")
        return {}
    except Exception as e:
        print(f"WARNING: {method} failed: {e}")
        return {}

def send_text(text):
    return tg_api("sendMessage", {
        "chat_id": CHAT_ID, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    })


# Load jobs
today_data = {}
p = Path("data/today_jobs.json")
if p.exists():
    try: today_data = json.loads(p.read_text())
    except: pass

jobs = today_data.get("jobs", [])
run_date = today_data.get("date", "today")

if not jobs:
    print("No jobs found in data/today_jobs.json")
    sys.exit(0)

top = [j for j in jobs if j["idx"] < 20]

ROLE_EMOJI = {"Product Manager":"🧩","Product Owner":"📋",
              "Business Analyst":"📊","Consultant/Strategy":"💼","Program Manager":"🗂"}

def score_dot(s):
    return "🟢" if s >= 75 else ("🟡" if s >= 60 else "🔴")

send_text(
    f"<b>🔁 Job Cards (resent) — {run_date}</b>\n"
    f"<i>Previous taps weren't saved — please tap ✅ again on the jobs you want</i>"
)

sent_msgs = {}
for job in top:
    idx   = job["idx"]
    sc    = job["score"]
    emoji = ROLE_EMOJI.get(job.get("role",""), "🔹")

    text = (
        f"{score_dot(sc)} <b>#{idx+1} · {sc}/100</b> {emoji} <b>{job['title']}</b>\n"
        f"🏢 {job['company']}"
    )
    if job.get("location"):
        text += f" · 📍 {job['location']}"
    text += f" · 📅 {job.get('date','')}"
    if job.get("salary"):
        text += f" · 💰 {job['salary']}"
    if job.get("url"):
        text += f'\n<a href="{job["url"]}">View →</a>'

    r = tg_api("sendMessage", {
        "chat_id": CHAT_ID, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": [[
            {"text": "✅ Shortlist", "callback_data": f"sl:{idx}"},
            {"text": "❌ Skip",      "callback_data": f"sk:{idx}"},
        ]]},
    })
    if r.get("ok") and r.get("result"):
        sent_msgs[str(idx)] = r["result"]["message_id"]

send_text("Tap ✅ on all the jobs you want, then send /apply for your Excel.")

# Update sent_messages.json
with open("data/sent_messages.json", "w") as f:
    json.dump({"date": run_date, "messages": sent_msgs}, f, indent=2)

print(f"Resent {len(top)} cards.")
sys.exit(0)
