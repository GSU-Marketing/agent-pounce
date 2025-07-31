"""
GSU Chat-Botty – all-in-one FastAPI backend
------------------------------------------
• GET  /              → {"status":"ok"}
• POST /chat          → OpenAI chat completion
• GET  /crawl         → Scrapes graduate program cards from graduate.gsu.edu
• POST /status        → Hits Slate Open API for applicant status
• GET  /iframe        → Tiny HTML+JS chat client for easy embedding
"""

# ---------- standard libs ----------
import os, logging
from datetime import datetime

# ---------- third-party ----------
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    log.warning("OPENAI_API_KEY not set! /chat will 500.")
client = OpenAI()                                   # auto-reads env var

SLATE_URL   = os.getenv(
    "SLATE_URL",
    "https://gradapply.gsu.edu/manage/service/api/gradtestbot"
)
SLATE_TOKEN = os.getenv(
    "SLATE_TOKEN",
    "1e5b8e64-548b-4341-843a-9a9bbbef92da"
)

# ---------- FastAPI ----------
app = FastAPI(
    title="GSU Chat-Botty Backend",
    version="1.0.0",
    description="FastAPI service powering the GPT admissions bot.",
)

# Allow browser JS from anywhere (lock this down in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 0. health ----------
@app.get("/", include_in_schema=False)
def health():
    """Render’s health-check & quick sanity ping."""
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# ---------- 1. /chat ----------
class ChatQuery(BaseModel):
    message: str = Field(..., examples=["Hello!"])

@app.post("/chat")
async def chat(query: ChatQuery):
    """Relay a single-turn chat completion."""
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY not configured")

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",          # switch to gpt-4o-mini if your key supports it
            messages=[
                {"role": "system", "content": "You are a helpful bot."},
                {"role": "user",   "content": query.message},
            ],
            temperature=0.7,
        )
        log.info("Chat completion ok (%s tokens)", completion.usage.total_tokens)
        return completion.model_dump()

    except Exception as e:                  # surface any OpenAI error
        log.exception("OpenAI failure")
        raise HTTPException(500, str(e)) from e

# ---------- 2. /crawl ----------
async def fetch_program_cards(url="https://graduate.gsu.edu/program-cards/"):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(url)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for card in soup.select("a.program-card"):
        yield {
            "title":  card.select_one(".program-card__title").get_text(strip=True),
            "degree": card.select_one(".program-card__degree").text.strip(),
            "link":   card["href"],
        }

@app.get("/crawl")
async def crawl():
    """Return the live list of graduate program cards."""
    return [c async for c in fetch_program_cards()]

# ---------- 3. /status ----------
class StatusReq(BaseModel):
    email: str       = Field(..., examples=["jaguar@gsu.edu"])
    birthdate: str   = Field(..., examples=["1999-05-14"])  # YYYY-MM-DD
    application_id: str = Field(..., examples=["A1234567"])

@app.post("/status")
async def status(req: StatusReq):
    """Proxy applicant look-up to Slate Open API."""
    headers = {"Authorization": f"Bearer {SLATE_TOKEN}"}
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.post(SLATE_URL, json=req.dict(), headers=headers)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            # Bubble Slate’s message up for easier debugging
            raise HTTPException(e.response.status_code, e.response.text) from e

# ---------- 4. /iframe ----------
CHAT_IFRAME = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>GSU Chat-Botty</title>
<style>
body,html{{margin:0;height:100%;font-family:system-ui}}
#log{{height:calc(100% - 42px);overflow:auto;padding:8px}}
#form{{height:42px;display:flex}}
#msg{{flex:1;border:1px solid #aaa;border-right:0;padding:4px}}
button{{width:80px}}
.user{{font-weight:bold;color:#0055CC}}
.bot{{color:#333}}
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
form.onsubmit = async (e) => {{
  e.preventDefault();
  const text = msgBox.value.trim();
  if(!text) return;
  logDiv.innerHTML += `<div class='user'>🧑‍🎓 ${text}</div>`;
  msgBox.value='';
  logDiv.scrollTop = logDiv.scrollHeight;
  const r = await fetch('/chat', {{
    method:'POST',
    headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{message:text}})
  }});
  const js = await r.json();
  const resp = js.choices?.[0]?.message?.content || '[error]';
  logDiv.innerHTML += `<div class='bot'>🐾 ${resp}</div>`;
  logDiv.scrollTop = logDiv.scrollHeight;
}};
</script>
</body>
</html>
"""

from fastapi.responses import HTMLResponse

@app.get("/iframe", response_class=HTMLResponse, include_in_schema=False)
def iframe():
    """Self-contained chat widget page."""
    return CHAT_IFRAME
