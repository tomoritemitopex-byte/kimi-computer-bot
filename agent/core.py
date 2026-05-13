import json
import time
from typing import AsyncGenerator

from .llm import LLMClient
from .tools import TOOL_DEFINITIONS, dispatch_tool

AGENT_SYSTEM_PROMPT = """You are Kimi Computer — an autonomous AI agent by Moonshot AI.

You have full computer access:
1. **Web Search** — DuckDuckGo search for real-time info
2. **Web Browsing** — Fetch and analyze any webpage
3. **Code Execution** — Run Python in a sandbox
4. **Terminal** — Shell commands (ls, cat, curl, python, pip, etc.)
5. **File System** — Read, write, manage files at /tmp/workspace

How you operate (like Moonshot's Kimi):
- Be PROACTIVE. Don't just answer — search, browse, execute, explore
- When asked a question, search DuckDuckGo first for current info
- Break complex tasks into parallel steps
- Show your thinking and tool usage transparently
- If one approach fails, try another
- Use the workspace for file operations
- You have persistent memory within this session"""


class Agent:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        ]

    async def run(self) -> AsyncGenerator[dict, None]:
        step = 0
        max_steps = 10

        yield {"type": "status", "content": "Starting agent..."}

        while step < max_steps:
            step += 1
            yield {"type": "step", "content": f"Step {step}: Thinking...", "step": step}

            try:
                response = await self.llm.chat_completion(
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                )
            except Exception as e:
                yield {"type": "error", "content": f"LLM call failed: {str(e)}"}
                break

            choice = response["choices"][0]
            msg = choice["message"]

            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        fn_args = {}

                    yield {
                        "type": "tool_call",
                        "tool": fn_name,
                        "args": fn_args,
                        "step": step,
                    }

                    result = await dispatch_tool(fn_name, fn_args)
                    result_preview = result[:500] + "..." if len(result) > 500 else result

                    yield {
                        "type": "tool_result",
                        "tool": fn_name,
                        "result": result_preview,
                        "step": step,
                    }

                    self.messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc],
                    })
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })
            else:
                content = msg.get("content", "") or ""
                yield {"type": "final", "content": content, "step": step}
                self.messages.append({"role": "assistant", "content": content})
                return

        yield {"type": "error", "content": "Agent reached maximum steps without a final answer."}
