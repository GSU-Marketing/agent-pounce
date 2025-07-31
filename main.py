# ---------- imports ----------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai, os

# ---------- keys ----------
openai.api_key = os.getenv("OPENAI_API_KEY")   # make sure this env var is set in Render

# ---------- create ONE FastAPI app ----------
app = FastAPI()

# ---------- CORS (let browser JS talk to us) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # later restrict to your domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- routes ----------
@app.get("/", include_in_schema=False)
def health():
    return {"status": "ok"}      # heartbeat page

class ChatQuery(BaseModel):
    message: str

@app.post("/chat")
async def chat(query: ChatQuery):
    """Simple echo to OpenAI"""
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": query.message}
        ],
        temperature=0.7,
    )
    # hand the whole response back to the browser
    return resp.dict()
