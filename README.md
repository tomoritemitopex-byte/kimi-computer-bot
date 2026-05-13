# Kimi Computer Bot

Autonomous AI agent with web browsing, code execution, terminal, and file system access — powered by NVIDIA NIM.

Stack: FastAPI + SSE streaming + Neon PostgreSQL

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your keys
python main.py
```

## Deploy on pella.app

1. Push this repo to GitHub
2. Import on pella.app — it auto-detects Python/FastAPI
3. Set env vars in pella dashboard:
   - `NVIDIA_API_KEY`
   - `DATABASE_URL` (Neon PostgreSQL)
4. Open the URL — you get a chat interface

## Models (NVIDIA NIM)

Switch models in the UI dropdown:
- `mistral-nemotron` — free, built for function calling
- `kimi-k2-instruct` — free, Kimi's own model
- `meta/llama-3.3-70b-instruct` — reliable default
- `deepseek-v4-flash` — fast, 1M context, agent-optimized
- `qwen3-coder-480b-a35b-instruct` — free, agentic coding
