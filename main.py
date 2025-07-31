"""
GSU Chat-Botty backend  v1.2-debug
• GET  /              → health-check
• POST /chat          → OpenAI chat completion
• GET  /crawl         → program cards
• GET  /status        → flexible 3-ID Slate lookup
• GET  /iframe        → mini chat widget
"""

# ---------- stdlib ----------
import os, logging
from datetime import datetime
from typing import Optional

# ---------- third-party ----------
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from openai import OpenAI
import httpx
from bs4 import BeautifulSoup

# ---------- logging ----------
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("gsu-chat-botty")

# ---------- env ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")           # must be set in Render
client = OpenAI()                                     # ← missing in your paste

SLATE_URL   = (
    "https://gradapply.gsu.edu/manage/query/run"
    "?id=0b17bc0d-6d90-444b-b581-206c7176df0e"
    "&cmd=service&output=json"
)
SLATE_USER  = "chatbot"                               # Name you typed in “User Token”
SLATE_TOKEN = "49704e7d-0520-4036-a611-a631bc6c750c"  # token value

# ---------- FastAPI ----------
app = FastAPI(title="GSU Chat-Botty", version="1.2-debug")
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- 0. health ----------
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def health():
    return {"status": "ok", "utc": datetime.utcnow().isoformat()}

# ---------- 1. /chat ----------
class ChatQuery(BaseModel):
    message: str

@app.post("/chat")
async def chat(q: ChatQuery):
    try:
        comp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful bot."},
                      {"role": "user",   "content": q.message}],
        )
        return comp.model_dump()
    except Exception as e:
        log.exception("OpenAI error")
        raise HTTPException(500, str(e))

# ---------- 2. /crawl ----------
async def fetch_program_cards(url="https://graduate.gsu.edu/program-cards/"):
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126 Safari/537.36")
    }
    async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as c:
        r = await c.get(url); r.raise_for_status()

    soup  = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("a.program-card, li.card")
    for card in cards:
        yield {
            "title":  card.select_one(".program-card__title, .card__title").get_text(strip=True),
            "degree": card.select_one(".program-card__degree, .card__degree").get_text(strip=True),
            "link":   card.get("href") or card.select_one("a")["href"],
        }

@app.get("/crawl")
async def crawl():
    data = [c async for c in fetch_program_cards()]
    if not data:
        log.warning("Crawler found 0 cards — selector may need update.")
    return data

# ---------- helper ----------
def _safe_json(resp: httpx.Response) -> dict:
    ctype = resp.headers.get("content-type", "")
    if "application/json" not in ctype.lower():
        raise HTTPException(
            502,
            f"Slate returned non-JSON ({resp.status_code}) – "
            "check Web-Service auth settings."
        )
    return resp.json()

# ---------- 3. /status ----------
class StatusReq(BaseModel):
    email:      Optional[str] = None
    birthdate:  Optional[str] = None  # YYYY-MM-DD
    panther_id: Optional[str] = None
    phone:      Optional[str] = None
    last_name:  Optional[str] = None
    program:    Optional[str] = None  # optional hint

def _have_3(d: dict) -> bool:
    return sum(bool(d.get(k)) for k in
               ("email", "birthdate", "panther_id", "phone", "last_name")) >= 3

@app.get("/status")
async def status(req: StatusReq = Depends()):
    params = req.dict(exclude_none=True)
    params.update({"user": SLATE_USER, "token": SLATE_TOKEN})   # 👈 query-string creds

    if not _have_3(params):
        raise HTTPException(422, "Need any three of: email, birthdate, panther_id, phone, last_name")

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
        try:
            r = await c.get(SLATE_URL, params=params); r.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error("Slate replied %s → %s", e.response.status_code,
                      e.response.text[:120])
            raise HTTPException(e.response.status_code, "Slate error") from e

    rows = _safe_json(r).get("data", [])
    if not rows:
        raise HTTPException(404, "No application matched")

    row = rows[0]
    return {
        "reference": row.get("Application_Reference_Id"),
        "first_name": row.get("First_Name"),
        "last_name":  row.get("Last_Name"),
        "status":     row.get("Application_Status"),
        "program":    row.get("Applied_Program"),
        "term":       row.get("Applied_Term"),
        "college":    row.get("Applied_College"),
        "email":      row.get("Email"),
        "phone":      row.get("Phone"),
        "birthdate":  row.get("birthdate"),
    }

# ---------- 4. /iframe ----------
CHAT_IFRAME = """<!doctype html><html><head>
<meta charset="utf-8"><title>GSU Chat</title>
<style>
body,html{margin:0;height:100%;font-family:system-ui}
#log{height:calc(100% - 42px);overflow:auto;padding:8px}
#form{height:42px;display:flex}
#msg{flex:1;border:1px solid #aaa;border-right:0;padding:4px}
button{width:80px}
.user{font-weight:bold;color:#0055CC}
.bot{color:#333}
</style></head><body>
<div id="log"></div>
<form id="form"><input id="msg" autocomplete="off" placeholder="Ask me anything…">
<button>Send</button></form>
<script>
const log=document.getElementById('log'),form=document.getElementById('form'),msg=document.getElementById('msg');
form.onsubmit=async e=>{
  e.preventDefault();
  const t=msg.value.trim(); if(!t)return;
  log.innerHTML+=`<div class='user'>🧑‍🎓 ${t}</div>`; msg.value=''; log.scrollTop=log.scrollHeight;
  const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:t})});
  const j=await r.json(), a=j.choices?.[0]?.message?.content||'[error]';
  log.innerHTML+=`<div class='bot'>🐾 ${a}</div>`; log.scrollTop=log.scrollHeight;
};
</script></body></html>"""

@app.get("/iframe", response_class=HTMLResponse, include_in_schema=False)
def iframe():
    return CHAT_IFRAME
