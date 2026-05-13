import os
import uuid
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from agent.llm import LLMClient
from agent.core import Agent
from db import init_db, close_db, save_message


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


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
