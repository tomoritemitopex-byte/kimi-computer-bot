import json

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a webpage and extract its text content and links",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using a query and return results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code in a sandboxed environment and return stdout/stderr",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (max 30)",
                        "default": 15,
                    },
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal",
            "description": "Run a shell command and return its output. Allowed: ls, cat, pwd, echo, python, pip, curl, wget, grep, find, head, tail, wc, sort, uniq, date, whoami, ps, df, du, mkdir, rm (files only), cp, mv, touch, chmod",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (max 30)",
                        "default": 15,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file (creates parent directories if needed)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to list",
                        "default": "/tmp/workspace",
                    }
                },
                "required": [],
            },
        },
    },
]


async def dispatch_tool(name: str, args: dict) -> str:
    from tools.browser import web_fetch as do_fetch, web_search as do_search
    from tools.code_exec import execute_code as do_code
    from tools.terminal import run_terminal as do_terminal
    from tools.filesystem import read_file as do_read, write_file as do_write, list_files as do_list

    tool_map = {
        "web_fetch": do_fetch,
        "web_search": do_search,
        "execute_code": do_code,
        "run_terminal": do_terminal,
        "read_file": do_read,
        "write_file": do_write,
        "list_files": do_list,
    }

    fn = tool_map.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = await fn(**args)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})
