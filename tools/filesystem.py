import os
from pathlib import Path

WORKSPACE = Path("/tmp/workspace")


def _resolve_path(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = WORKSPACE / p
    p = p.resolve()
    os.makedirs(WORKSPACE, exist_ok=True)
    return p


async def read_file(path: str) -> dict:
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if not p.is_file():
            return {"error": f"Not a file: {path}"}

        content = p.read_text(encoding="utf-8", errors="replace")
        size = len(content)
        if size > 50000:
            content = content[:50000] + "\n\n... [File truncated at 50000 chars]"

        return {
            "path": str(p),
            "content": content,
            "size": size,
            "lines": content.count("\n") + 1,
        }
    except Exception as e:
        return {"error": str(e)}


async def write_file(path: str, content: str) -> dict:
    try:
        p = _resolve_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {
            "path": str(p),
            "size": len(content),
            "status": "written",
        }
    except Exception as e:
        return {"error": str(e)}


async def list_files(path: str = "/tmp/workspace") -> dict:
    try:
        p = _resolve_path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}", "files": []}
        if not p.is_dir():
            return {"error": f"Not a directory: {path}", "files": []}

        entries = []
        for entry in sorted(p.iterdir()):
            try:
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
            except OSError:
                entries.append({"name": entry.name, "type": "unknown"})

        return {"path": str(p), "files": entries, "count": len(entries)}
    except Exception as e:
        return {"error": str(e), "files": []}
