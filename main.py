# ---------- imports ----------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import httpx, os
from bs4 import BeautifulSoup

# ---------- OpenAI client ----------
client = OpenAI()                           # uses OPENAI_API_KEY env var

# ---------- FastAPI app ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                    # tighten later
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- heartbeat ----------
@app.get("/", include_in_schema=False)
def health():
    return {"status": "ok"}

# ---------- /chat ----------
class ChatQuery(BaseModel):
    message: str                            # {"message":"Hi"}

@app.post("/chat")
async def chat(query: ChatQuery):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful bot."},
            {"role": "user",   "content": query.message},
        ],
    )
    return completion.model_dump()          # <- function ends here

# ---------- crawler helpers ----------
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
    # gather generator output into a list
    return [c async for c in fetch_program_cards()]
