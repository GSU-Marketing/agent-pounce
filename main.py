"""
GSU Chat-Botty – all-in-one FastAPI backend
------------------------------------------
• GET  /              → {"status": "ok"}
• POST /chat          → OpenAI chat completion
• GET  /crawl         → Scrape graduate program cards from graduate.gsu.edu
• GET  /status        → Applicant status via Slate Open API
• GET  /iframe        → Self-contained HTML chat widget
"""

# ---------- standard libs ----------
import os, logging
from datetime import datetime

# ---------- third-party ----------
from fastapi import FastAPI, HTTPException, Depends            # ← Depends added here
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from openai import OpenAI
import httpx
from bs4 import BeautifulSoup

# ---------- logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("gsu-chat-botty")

# ---------- environment ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    log.warning("OPENAI_API_KEY not set – /chat will fail.")
client = OpenAI()  # auto-reads env var

SLATE_URL   = os.getenv("SLATE_URL",   "https://gradapply.gsu.edu/manage/service/api/gradtestbot")
SLATE_TOKEN = os.getenv("SLATE_TOKEN", "1e5b8e64-548b-4341-843a-9a9bbbef92da")

# ---------- FastAPI ----------
app = FastAPI(
    title="GSU Chat-Botty Backend",
    version="1.0.2",
    description="GPT chatbot + live crawler + Slate status.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 0. health ----------
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def health():
    return {"status": "ok", "utc": datetime.utcnow().isoformat()}

# ---------- 1. /chat ----------
class ChatQuery(BaseModel):
    message: str = Field(..., examples=["Hello!"])

@app.post("/chat")
async def chat(query: ChatQuery):
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY not configured")

    try:
        comp = client.chat.completions.create(
            model="gpt-3.5-turbo",       # use gpt-4o-mini if your key allows
            messages=[
                {"role": "system", "content": "You are a helpful bot."},
                {"role": "user",   "content": query.message},
            ],
            temperature=0.7,
        )
        return comp.model_dump()
    except Exception as e:
        log.exception("OpenAI failure")
        raise HTTPException(500, str(e)) from e

# ---------- 2. /crawl ----------
async def fetch_program_cards(url: str = "https://graduate.gsu.edu/program-cards/"):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
        )
    }
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("a.program-card, li.card")  # handles both old & new markup

    for card in cards:
        title  = card.select_one(".program-card__title, .card__title")
        degree = card.select_one(".program-card__degree, .card__degree")
        link   = card.get("href") or card.select_one("a")["href"]
        yield {
            "title":  title.get_text(strip=True) if title else "N/A",
            "degree": degree.get_text(strip=True) if degree else "N/A",
            "link":   link,
        }

@app.get("/crawl")
async def crawl():
    return [c async for c in fetch_program_cards()]

# ---------- 3. /status ----------
class StatusReq(BaseModel):
    email: str         = Field(..., examples=["jaguar@gsu.edu"])
    birthdate: str     = Field(..., examples=["1999-05-14"])  # YYYY-MM-DD
    application_id: str = Field(..., examples=["A1234567"])

@app.get("/status")
async def status(req: StatusReq = Depends()):
    headers = {"Authorization": f"Bearer {SLATE_TOKEN}"}
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(SLATE_URL, params=req.dict(), headers=headers)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text) from e

    data = r.json().get("data", [])
    if not data:
        raise HTTPException(404, "Applicant not found")

    row = data[0]
    return {
        "reference":   row.get("Application_Reference_Id"),
        "first_name":  row.get("First_Name"),
        "last_name":   row.get("Last_Name"),
        "birthdate":   row.get("birthdate"),
        "phone":       row.get("Phone"),
        "email":       row.get("Email"),
        "status":      row.get("Application_Status"),
        "college":     row.get("Applied_College"),
        "program":     row.get("Applied_Program"),
        "term":        row.get("Applied_Term"),
    }

# ---------- 4. /iframe ----------
CHAT_IFRAME = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>GSU Chat-Botty</title>
<style>
body,html{margin:0;height:100%;font-family:system-ui}
#log{height:calc(100% - 42px);overflow:auto;padding:8px}
#form{height:42px;display:flex}
#msg{flex:1;border:1px solid #aaa;border-right:0;padding:4px}
button{width:80px}
.user{font-weight:bold;color:#0055CC}
.bot{color:#333}
</style>
</head>
<body>
<div id="log"></div>
<form id="form">
  <input id="msg" autocomplete="off" placeholder="Ask me anything…">
  <button>Send</button>
</form>
<script>
const logDiv = document.getElementById('log');
const form   = document.getElementById('form');
const msgBox = document.getElementById('msg');
form.onsubmit = async (e) => {
  e.preventDefault();
  const text = msgBox.value.trim();
  if (!text) return;
  logDiv.innerHTML += `<div class='user'>🧑‍🎓 ${text}</div>`;
  msgBox.value = '';
  logDiv.scrollTop = logDiv.scrollHeight;
  const r = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  });
  const js   = await r.json();
  const resp = js.choices?.[0]?.message?.content || '[error]';
  logDiv.innerHTML += `<div class='bot'>🐾 ${resp}</div>`;
  logDiv.scrollTop = logDiv.scrollHeight;
};
</script>
</body>
</html>
"""

@app.get("/iframe", response_class=HTMLResponse, include_in_schema=False)
def iframe():
    return CHAT_IFRAME
