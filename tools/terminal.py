import asyncio
import os
import shlex

ALLOWED_COMMANDS = {
    "ls", "cat", "pwd", "echo", "python", "pip", "curl", "wget",
    "grep", "find", "head", "tail", "wc", "sort", "uniq",
    "date", "whoami", "ps", "df", "du",
    "mkdir", "rm", "cp", "mv", "touch", "chmod", "chown",
    "tree", "which", "env", "id", "uname",
}


async def run_terminal(command: str, timeout: int = 15) -> dict:
    timeout = min(timeout, 30)

    parts = shlex.split(command)
    if not parts:
        return {"stdout": "", "stderr": "Empty command", "exit_code": -1}

    cmd_base = parts[0]
    if cmd_base not in ALLOWED_COMMANDS:
        return {
            "stdout": "",
            "stderr": f"Command '{cmd_base}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}",
            "exit_code": -1,
        }

    if cmd_base in ("rm",) and "-rf" in parts:
        return {
            "stdout": "",
            "stderr": "Recursive force delete (-rf) is not allowed for safety",
            "exit_code": -1,
        }

    try:
        proc = await asyncio.create_subprocess_exec(
            *parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp",
            env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")},
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
            }

        stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
        stderr_str = stderr.decode("utf-8", errors="replace")[:5000]

        return {
            "stdout": stdout_str.strip(),
            "stderr": stderr_str.strip(),
            "exit_code": proc.returncode,
        }
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"Command not found: {cmd_base}", "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}
