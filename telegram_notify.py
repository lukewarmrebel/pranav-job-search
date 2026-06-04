"""
Sends full Excel + interactive job cards to Telegram.
Reads from data/today_jobs.json (written by score_jobs.py).
"""
import json, os, sys, uuid, urllib.request, urllib.error
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

if not TOKEN or not CHAT_ID:
    print("WARNING: no credentials — skipping.")
    sys.exit(0)

# Load scored jobs (written by score_jobs.py before this runs)
try:
    with open("data/today_jobs.json") as f:
        today_data = json.load(f)
except Exception as e:
    print(f"ERROR reading data/today_jobs.json: {e}")
    sys.exit(0)

scored       = today_data.get("jobs", [])
run_date_str = today_data.get("date", "today")

if not scored:
    print("No scored jobs found — skipping.")
    sys.exit(0)


# ── Excel generation ──────────────────────────────────────────────────────────

def make_full_excel(jobs, date_str):
    if not HAS_OPENPYXL:
        return None
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "All Scored Jobs"

    HDR_FILL   = PatternFill("solid", fgColor="1F4E79")
    GREEN_FILL = PatternFill("solid", fgColor="E2EFDA")
    YELLOW_FILL= PatternFill("solid", fgColor="FFEB9C")
    RED_FILL   = PatternFill("solid", fgColor="FFC7CE")
    HDR_FONT   = Font(bold=True, color="FFFFFF", size=10)
    BD         = Side(style="thin", color="CCCCCC")
    BORDER     = Border(left=BD, right=BD, top=BD, bottom=BD)

    cols = ["#","Score","Role","Title","Company","Location","Date","Salary","Site","Apply URL"]
    ws.append(cols)
    for col in range(1, len(cols)+1):
        c = ws.cell(1, col)
        c.fill = HDR_FILL; c.font = HDR_FONT
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = BORDER

    for rank, j in enumerate(jobs, 1):
        sc = j["score"]
        row = [rank, sc, j.get("role",""), j["title"], j["company"],
               j.get("location",""), j.get("date",""), j.get("salary",""), j.get("site",""), j.get("url","")]
        ws.append(row)
        fill = GREEN_FILL if sc >= 75 else (YELLOW_FILL if sc >= 60 else RED_FILL)
        for col in range(1, len(row)+1):
            c = ws.cell(ws.max_row, col)
            c.fill = fill; c.border = BORDER
            c.alignment = Alignment(wrap_text=True, vertical="top")
        if j.get("url"):
            c = ws.cell(ws.max_row, 10)
            c.hyperlink = j["url"]
            c.font = Font(color="0563C1", underline="single")

    widths = [4, 6, 18, 42, 28, 20, 10, 14, 10, 12]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}1"

    ws2 = wb.create_sheet("Legend")
    for row, (color, label) in enumerate([
        ("E2EFDA","Score ≥75 — High match"),
        ("FFEB9C","Score 60–74 — Medium match"),
        ("FFC7CE","Score 55–59 — Lower match"),
    ], 1):
        ws2.cell(row,1).fill = PatternFill("solid", fgColor=color)
        ws2.cell(row,2).value = label

    path = f"/tmp/jobs_full_{date_str}.xlsx"
    wb.save(path)
    return path


# ── Telegram helpers ──────────────────────────────────────────────────────────

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
        print(f"WARNING: sendDocument HTTP {e.code}: {e.read().decode(errors='replace')}")
        return {}
    except Exception as e:
        print(f"WARNING: sendDocument failed: {e}")
        return {}


# ── send Excel ────────────────────────────────────────────────────────────────

excel_path = make_full_excel(scored, run_date_str)
if excel_path:
    res = send_document(excel_path,
                        caption=f"📊 Full scored jobs — {run_date_str} ({len(scored)} roles, score ≥55)")
    if res.get("ok"):
        print(f"✅ Excel sent ({len(scored)} jobs)")
    else:
        print(f"WARNING: Excel send result: {res}")
else:
    print("openpyxl not available — skipping Excel")


# ── send interactive job cards (top 20) ──────────────────────────────────────

ROLE_EMOJI = {"Product Manager":"🧩","Product Owner":"📋",
              "Business Analyst":"📊","Consultant/Strategy":"💼","Program Manager":"🗂"}

def score_dot(s):
    return "🟢" if s >= 75 else ("🟡" if s >= 60 else "🔴")

top = scored[:20]

send_text(
    f"<b>📌 Job Digest — {run_date_str}</b>\n"
    f"<i>{len(scored)} qualifying roles · Tap ✅ to shortlist, ❌ to skip</i>"
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

send_text(
    "━━━━━━━━━━━━━━━━━━━━\n"
    "💡 <b>How to use:</b>\n"
    "• Tap ✅ <b>Shortlist</b> to save a job\n"
    "• Paste any job URL to add it manually\n"
    "• /apply — get your final apply-list Excel\n"
    "• /status — see your shortlist count"
)

Path("data").mkdir(exist_ok=True)
with open("data/sent_messages.json", "w") as f:
    json.dump({"date": run_date_str, "messages": sent_msgs}, f, indent=2)

print(f"Done. {len(top)} interactive cards sent for {run_date_str}.")
sys.exit(0)
