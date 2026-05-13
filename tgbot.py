"""
Kimi Computer — Telegram Bot
Long polling bot that connects to the Kimi agent with DuckDuckGo search.
"""

import os, sys, json, asyncio, logging, uuid

import httpx
from agent.llm import LLMClient
from agent.core import Agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("kimi-tg")

BOT_TOKEN = os.getenv("BOT_TOKEN")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

SYSTEM = """You are Kimi Computer — an autonomous AI agent with full computer access.

Capabilities:
1. **Web Browsing** — Fetch web pages, search DuckDuckGo
2. **Code Execution** — Run Python code
3. **Terminal** — Shell commands
4. **File System** — Read/write files

Rules:
- Use DuckDuckGo search (web_search tool) when asked to find information
- Break down complex tasks into steps
- Show your thinking process
- When writing code, use Python
- Explain what you're doing
- The workspace is /tmp/workspace"""

def tg(method, data):
    try:
        r = httpx.post(f"{TG_API}/{method}", json=data, timeout=15)
        return r.json()
    except: return None

def tg_send(chat_id, text):
    for chunk in split(text, 4000):
        tg("sendMessage", {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"})
        log.info(f"Sent {len(chunk)} chars to {chat_id}")

def split(t, n):
    p = []
    while len(t) > n:
        i = n
        for s in ["\n\n", "\n", ". "]:
            idx = t.rfind(s, 0, n)
            if idx > n // 2: i = idx + len(s); break
        p.append(t[:i].strip())
        t = t[i:].strip()
    if t: p.append(t)
    return p

async def process_message(chat_id, text):
    tg("sendChatAction", {"chat_id": chat_id, "action": "typing"})

    llm = LLMClient(api_key=NVIDIA_KEY, model=os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"))
    agent = Agent(llm)
    agent.messages[0]["content"] = SYSTEM
    agent.messages.append({"role": "user", "content": text})

    full_response = ""
    async for event in agent.run():
        if event["type"] == "final":
            full_response = event["content"]
        elif event["type"] == "tool_call":
            log.info(f"  Tool: {event['tool']}({json.dumps(event['args'])})")
        elif event["type"] == "tool_result":
            log.info(f"  Result: {event['result'][:100]}...")
        elif event["type"] == "error":
            full_response = f"Error: {event['content']}"

    if full_response:
        tg_send(chat_id, full_response + f"\n\n—\n🤖 *Kimi Computer*")
    else:
        tg_send(chat_id, "No response generated.")

async def main():
    log.info("🚀 Kimi Computer Telegram Bot")
    log.info(f"Token: {'✅' if BOT_TOKEN else '❌'}")
    log.info(f"NVIDIA: {'✅' if NVIDIA_KEY else '❌'}")

    offset = 0
    log.info("📡 Polling...")
    while True:
        try:
            r = httpx.post(f"{TG_API}/getUpdates", json={
                "offset": offset, "timeout": 30, "allowed_updates": ["message"]
            }, timeout=35)
            if r.status_code != 200:
                await asyncio.sleep(5)
                continue
            for upd in r.json().get("result", []):
                msg = upd.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = msg.get("chat", {}).get("id")
                if text and chat_id and not text.startswith("/"):
                    log.info(f"📨 From {chat_id}: {text[:60]}...")
                    await process_message(chat_id, text)
                offset = upd["update_id"] + 1
        except Exception as e:
            log.error(f"Poll: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
