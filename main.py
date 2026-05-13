import os
import uuid
import json
import logging
import asyncio
import httpx
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from agent.llm import LLMClient
from agent.core import Agent
from db import init_db, close_db, save_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("kimi")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(title="Kimi Computer Bot", lifespan=lifespan)
sessions: dict[str, Agent] = {}

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index():
    html = STATIC_DIR / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Kimi Computer Bot</h1>")


@app.post("/chat")
async def create_chat(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    model = body.get("model", os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"))
    session_id = str(uuid.uuid4())

    await save_message(session_id, "user", message, model)

    llm = LLMClient(model=model)
    agent = Agent(llm)
    agent.messages.append({"role": "user", "content": message})
    sessions[session_id] = agent

    return {"session_id": session_id}


@app.get("/chat/{session_id}/stream")
async def stream_chat(session_id: str, request: Request):
    agent = sessions.get(session_id)
    if not agent:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    async def event_generator():
        try:
            async for event in agent.run():
                if await request.is_disconnected():
                    break
                yield {"event": event["type"], "data": json.dumps(event)}

                if event["type"] == "final":
                    await save_message(session_id, "assistant", event["content"], agent.llm.model)

                if event["type"] == "tool_call":
                    await save_message(
                        session_id, "tool_call", None,
                        tool_calls=[{"tool": event["tool"], "args": event["args"]}],
                    )

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
        finally:
            sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())


# ── Telegram helpers ──────────────────────────────────────

async def tg_send(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=15) as client:
        for chunk in _split(text, 4000):
            await client.post(f"{TG_API}/sendMessage", json={
                "chat_id": chat_id, "text": chunk, "parse_mode": "Markdown",
            })

def _split(text: str, n: int) -> list:
    parts = []
    while len(text) > n:
        i = n
        for s in ["\n\n", "\n", ". "]:
            idx = text.rfind(s, 0, n)
            if idx > n // 2: i = idx + len(s); break
        parts.append(text[:i].strip())
        text = text[i:].strip()
    if text: parts.append(text)
    return parts

async def handle_tg_message(chat_id: int, text: str):
    log.info(f"💬 From {chat_id}: {text[:80]}")
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(f"{TG_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

    llm = LLMClient()
    agent = Agent(llm)
    agent.messages.append({"role": "user", "content": text})

    step_count = 0
    full = ""
    tool_log = []
    async for event in agent.run():
        if event["type"] == "final":
            full = event["content"]
            if tool_log:
                full = "🧠 *Kimi Computer*\n\n" + full + "\n\n—\n🔧 Used: " + ", ".join(tool_log)
        elif event["type"] == "tool_call":
            step_count += 1
            tool_log.append(f"{event['tool']}")
            log.info(f"  🔧 Step {step_count}: {event['tool']}({json.dumps(event['args'])[:80]})")
        elif event["type"] == "error":
            full = f"⚠️ Error: {event['content']}"

    if full:
        await tg_send(chat_id, full)
    else:
        await tg_send(chat_id, "No response generated.")

# ── Telegram webhook endpoint ─────────────────────────────

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    msg = update.get("message", {})
    text = msg.get("text", "").strip()
    chat_id = msg.get("chat", {}).get("id")
    if text and chat_id and not text.startswith("/"):
        asyncio.ensure_future(handle_tg_message(chat_id, text))
    return {"ok": True}

@app.get("/set-webhook")
async def set_webhook(request: Request):
    url = str(request.base_url).rstrip("/") + "/telegram-webhook"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{TG_API}/setWebhook?url={url}&drop_pending_updates=true")
        return r.json()

# ── Start ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log.info(f"🚀 Kimi Computer")
    log.info(f"   Token: {'✅' if BOT_TOKEN else '❌'}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
