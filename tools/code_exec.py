import asyncio
import tempfile
import os

ALLOWED_MODULES = {
    "math", "random", "json", "re", "collections", "itertools", "datetime",
    "statistics", "string", "typing", "functools", "pathlib",
}


async def execute_code(code: str, timeout: int = 15) -> dict:
    timeout = min(timeout, 30)

    safe_code = f"""import sys, json, traceback
{chr(10).join(f"import {m}" for m in ALLOWED_MODULES)}

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except Exception as e:
    print("ERROR:", traceback.format_exc(), file=sys.stderr)
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(safe_code)
        fpath = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            fpath,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp",
            env={"PYTHONIOENCODING": "utf-8", "PATH": os.environ.get("PATH", "")},
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
                "stderr": "",
                "error": f"Execution timed out after {timeout}s",
                "exit_code": -1,
            }

        stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
        stderr_str = stderr.decode("utf-8", errors="replace")[:5000]

        return {
            "stdout": stdout_str,
            "stderr": stderr_str,
            "exit_code": proc.returncode,
        }
    except Exception as e:
        return {"stdout": "", "stderr": "", "error": str(e), "exit_code": -1}
    finally:
        try:
            os.unlink(fpath)
        except OSError:
            pass
