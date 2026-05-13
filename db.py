import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: asyncpg.Pool | None = None


async def init_db():
    global _pool
    if not DATABASE_URL:
        return
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                model TEXT,
                tool_calls JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session
            ON conversations(session_id)
        """)


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def save_message(
    session_id: str,
    role: str,
    content: str | None,
    model: str | None = None,
    tool_calls: list | None = None,
):
    if not _pool:
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversations (session_id, role, content, model, tool_calls)
            VALUES ($1, $2, $3, $4, $5)
            """,
            session_id, role, content, model,
            tool_calls,
        )


async def get_history(session_id: str, limit: int = 50):
    if not _pool:
        return []
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content, tool_calls, created_at
            FROM conversations
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            session_id, limit,
        )
        return [dict(r) for r in rows]
