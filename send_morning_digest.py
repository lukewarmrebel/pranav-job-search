"""
Called by GitHub Actions after Claude pushes output/jobs_*.xlsx.
Sends the pre-generated Excel to Telegram, then sends interactive job cards.
"""
import json, os, sys, uuid, urllib.request, urllib.error
from pathlib import Path

TOKEN     = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
EXCEL_PATH = os.environ.get("EXCEL_PATH", "")

if not TOKEN or not CHAT_ID:
    print("WARNING: no credentials — skipping."); sys.exit(0)


def tg_api(method, payload):
    url  = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"WARNING: {method} HTTP {e.code}: {e.read().decode(errors='replace')}"); return {}
    except Exception as e:
        print(f"WARNING: {method} failed: {e}"); return {}

def send_text(text):
    return tg_api("sendMessage", {
        "chat_id": CHAT_ID, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    })

def send_document(path, caption=""):
    boundary = uuid.uuid4().hex
    filename = os.path.basename(path)
    with open(path, "rb") as f:
        file_bytes = f.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{CHAT_ID}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    req = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"WARNING: sendDocument HTTP {e.code}: {e.read().decode(errors='replace')}"); return {}
    except Exception as e:
        print(f"WARNING: sendDocument failed: {e}"); return {}


# ── Send Excel ─────────────────────────────────────────────────────────────────

if EXCEL_PATH and Path(EXCEL_PATH).exists():
    today_data = {}
    try:
        with open("data/today_jobs.json") as f:
            today_data = json.load(f)
    except Exception:
        pass
    run_date = today_data.get("date", "today")
    total    = len(today_data.get("jobs", []))

    res = send_document(EXCEL_PATH,
                        caption=f"📊 Job Digest — {run_date}  |  {total} scored roles  |  Scored & ranked by Claude")
    if res.get("ok"):
        print(f"✅ Excel sent: {EXCEL_PATH}")
    else:
        print(f"WARNING: Excel send failed: {res}")
else:
    print(f"WARNING: Excel not found at {EXCEL_PATH!r}")


# ── Send interactive job cards ─────────────────────────────────────────────────

try:
    with open("data/today_jobs.json") as f:
        today_data = json.load(f)
except Exception as e:
    print(f"ERROR reading today_jobs.json: {e}"); sys.exit(0)

jobs         = today_data.get("jobs", [])
run_date_str = today_data.get("date", "today")
top          = [j for j in jobs if j.get("idx", 999) < 20]

if not top:
    print("No jobs to send as cards."); sys.exit(0)

ROLE_EMOJI = {"Product Manager":"🧩","Product Owner":"📋",
              "Business Analyst":"📊","Consultant/Strategy":"💼","Program Manager":"🗂"}

def dot(s):
    return "🟢" if s >= 75 else ("🟡" if s >= 60 else "🔴")

send_text(
    f"<b>📌 Job Digest — {run_date_str}</b>\n"
    f"<i>Scored &amp; ranked by Claude · {len(jobs)} qualifying roles · Tap ✅ to shortlist</i>"
)

sent_msgs = {}
for job in top:
    idx   = job["idx"]
    sc    = job["score"]
    emoji = ROLE_EMOJI.get(job.get("role", ""), "🔹")
    text  = (
        f"{dot(sc)} <b>#{idx+1} · {sc}/100</b> {emoji} <b>{job['title']}</b>\n"
        f"🏢 {job['company']}"
    )
    if job.get("location"): text += f" · 📍 {job['location']}"
    text += f" · 📅 {job.get('date','')}"
    if job.get("salary"):   text += f" · 💰 {job['salary']}"
    if job.get("url"):      text += f'\n<a href="{job["url"]}">View →</a>'

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
    "━━━━━━━━━━━━━━━━━━━━\n"
    "• Tap ✅ <b>Shortlist</b> / ❌ <b>Skip</b> on each job\n"
    "• Paste any job URL to add manually\n"
    "• /apply — quick apply-list Excel\n"
    "• /status — see your shortlist"
)

Path("data").mkdir(exist_ok=True)
with open("data/sent_messages.json", "w") as f:
    json.dump({"date": run_date_str, "messages": sent_msgs}, f, indent=2)

print(f"✅ Sent {len(top)} interactive cards for {run_date_str}.")
sys.exit(0)
