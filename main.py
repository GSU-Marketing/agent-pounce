# ---------- imports ----------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI       # ← NEW library, replaces old “openai.ChatCompletion”
import os

# ---------- OpenAI client ----------
client = OpenAI()               # uses OPENAI_API_KEY env var automatically

# ---------- FastAPI app ----------
app = FastAPI()

# CORS: let browser JS call the API (tighten allow_origins in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- heartbeat ----------
@app.get("/", include_in_schema=False)
def health():
    return {"status": "ok"}

# ---------- chat endpoint ----------
class ChatQuery(BaseModel):
    message: str                # JSON shape: {"message":"Hi"}

@app.post("/chat")
async def chat(query: ChatQuery):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",  # or gpt-4o-mini if your key has access
        messages=[
            {"role": "system", "content": "You are a helpful bot."},
            {"role": "user",   "content": query.message},
        ],
        temperature=0.7,
    )
    return completion.model_dump()   # full JSON back to caller
