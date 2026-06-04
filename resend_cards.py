"""
Resends today's interactive job cards, marking already-shortlisted ones clearly.
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
p = Path("data/today_jobs.json")
if not p.exists():
    print("data/today_jobs.json not found"); sys.exit(0)
today_data = json.loads(p.read_text())
jobs       = today_data.get("jobs", [])
run_date   = today_data.get("date", "today")

if not jobs:
    print("No jobs found"); sys.exit(0)

# Load current shortlist so we can mark saved ones
sl_path = Path("data/shortlisted.json")
saved_idxs = set()
if sl_path.exists():
    try:
        sl = json.loads(sl_path.read_text())
        saved_idxs = {j["idx"] for j in sl.get("jobs", [])}
    except Exception:
        pass

top = [j for j in jobs if j["idx"] < 20]

ROLE_EMOJI = {"Product Manager":"🧩","Product Owner":"📋",
              "Business Analyst":"📊","Consultant/Strategy":"💼","Program Manager":"🗂"}

def score_dot(s):
    return "🟢" if s >= 75 else ("🟡" if s >= 60 else "🔴")

saved_count   = sum(1 for j in top if j["idx"] in saved_idxs)
unsaved_count = len(top) - saved_count

send_text(
    f"<b>🔁 Job Cards (resent) — {run_date}</b>\n"
    f"<i>✅ {saved_count} already saved · {unsaved_count} still need your input</i>\n\n"
    f"Already-saved jobs are marked below. Tap ✅ on any you missed."
)

sent_msgs = {}
for job in top:
    idx   = job["idx"]
    sc    = job["score"]
    emoji = ROLE_EMOJI.get(job.get("role",""), "🔹")
    dot   = score_dot(sc)

    if idx in saved_idxs:
        # Show as saved — no keyboard needed
        text = (
            f"✅ <b>SAVED</b> {dot} #{idx+1} · {sc}/100 {emoji} <b>{job['title']}</b>\n"
            f"🏢 {job['company']}"
        )
        if job.get("location"):
            text += f" · 📍 {job['location']}"
        if job.get("url"):
            text += f'\n<a href="{job["url"]}">View →</a>'
        tg_api("sendMessage", {
            "chat_id": CHAT_ID, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        })
    else:
        # Normal card with ✅/❌ buttons
        text = (
            f"{dot} <b>#{idx+1} · {sc}/100</b> {emoji} <b>{job['title']}</b>\n"
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

send_text(
    f"Tap ✅ on any jobs above you want to add.\n"
    f"Send /apply when done for your final Excel."
)

# Update sent_messages.json with new message IDs
sm_path = Path("data/sent_messages.json")
existing_sm = {}
if sm_path.exists():
    try: existing_sm = json.loads(sm_path.read_text())["messages"]
    except: pass
existing_sm.update(sent_msgs)
with open("data/sent_messages.json", "w") as f:
    json.dump({"date": run_date, "messages": existing_sm}, f, indent=2)

print(f"Resent {len(top)} cards ({saved_count} already saved, {unsaved_count} still need input).")
sys.exit(0)
