"""
Called by GitHub Actions after Claude pushes output/apply_*.xlsx.
Sends the pre-generated apply-list Excel to Telegram.
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


if not EXCEL_PATH or not Path(EXCEL_PATH).exists():
    print(f"WARNING: Apply list Excel not found at {EXCEL_PATH!r}"); sys.exit(0)

# Read counts from shortlisted/manual for caption
shortlisted_count = 0
manual_count = 0
run_date = "today"

try:
    with open("data/shortlisted.json") as f:
        sl = json.load(f)
    shortlisted_count = len(sl.get("jobs", []))
    run_date = sl.get("date", run_date)
except Exception:
    pass

try:
    with open("data/manual_jobs.json") as f:
        manual = json.load(f)
    manual_count = len(manual.get("entries", []))
    if not run_date or run_date == "today":
        run_date = manual.get("date", run_date)
except Exception:
    pass

total = shortlisted_count + manual_count
caption = (
    f"📋 Apply List — {run_date}\n"
    f"✅ {shortlisted_count} shortlisted  +  🔗 {manual_count} manual\n"
    f"Total: {total} jobs to action"
)

res = send_document(EXCEL_PATH, caption=caption)
if res.get("ok"):
    print(f"✅ Apply list Excel sent: {EXCEL_PATH}")
    send_text(
        f"📋 <b>Apply List ready — {run_date}</b>\n"
        f"✅ {shortlisted_count} shortlisted  +  🔗 {manual_count} manual URLs\n\n"
        f"The Excel above has 3 sheets:\n"
        f"• <b>Apply List</b> — jobs to action today\n"
        f"• <b>Full Decision Log</b> — all scored jobs with Apply/Skip/Pending status\n"
        f"• <b>Manual Jobs Detail</b> — enriched details for URLs you shared"
    )
else:
    print(f"WARNING: Apply list send failed: {res}")

sys.exit(0)
