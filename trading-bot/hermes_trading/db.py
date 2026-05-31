"""Supabase/Postgres persistence layer.

Falls back to local file state if DATABASE_URL is not set.
Tables are created automatically on first connect.
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

_pool = None


async def _get_pool():
    global _pool
    if _pool is not None:
        return _pool
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return None
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=3, ssl="require")
        await _init_schema(_pool)
        log.info("Connected to Supabase Postgres")
    except Exception as exc:
        log.warning(f"DB connection failed, using local files: {exc}")
        _pool = None
    return _pool


async def _init_schema(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS strategies (
                id SERIAL PRIMARY KEY,
                version TEXT NOT NULL,
                data JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS hypotheses (
                id SERIAL PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS heartbeat (
                id INT PRIMARY KEY DEFAULT 1,
                data JSONB NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)


async def append_trade(trade: dict) -> None:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO trades (data) VALUES ($1)", json.dumps(trade))
    else:
        from pathlib import Path
        import os
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        with open(state / "trades.jsonl", "a") as f:
            f.write(json.dumps(trade) + "\n")


async def load_trades(limit: int = 500) -> list[dict]:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT data FROM trades ORDER BY created_at DESC LIMIT $1", limit
            )
            return [json.loads(r["data"]) for r in reversed(rows)]
    else:
        from pathlib import Path
        import os
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        path = state / "trades.jsonl"
        if not path.exists():
            return []
        lines = [l for l in path.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
        return [json.loads(l) for l in lines[-limit:]]


async def save_strategy(version: str, data: dict) -> None:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO strategies (version, data) VALUES ($1, $2)",
                version, json.dumps(data)
            )
    else:
        import yaml
        from pathlib import Path
        import os
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        with open(state / "strategy.yaml", "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


async def append_hypothesis(h: dict) -> None:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO hypotheses (data) VALUES ($1)", json.dumps(h))
    else:
        from pathlib import Path
        import os
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        with open(state / "hypotheses.jsonl", "a") as f:
            f.write(json.dumps({**h, "ts": datetime.now(timezone.utc).isoformat()}) + "\n")


async def write_heartbeat(data: dict) -> None:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO heartbeat (id, data, updated_at) VALUES (1, $1, NOW())
                ON CONFLICT (id) DO UPDATE SET data = $1, updated_at = NOW()
            """, json.dumps(data))
    else:
        from pathlib import Path
        import os
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        with open(state / "heartbeat.json", "w") as f:
            json.dump(data, f)


async def read_heartbeat() -> dict:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM heartbeat WHERE id = 1")
            return json.loads(row["data"]) if row else {}
    else:
        from pathlib import Path
        import os
        import json as _json
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        try:
            return _json.loads((state / "heartbeat.json").read_text(encoding="utf-8-sig"))
        except Exception:
            return {}


async def load_hypotheses(limit: int = 50) -> list[dict]:
    pool = await _get_pool()
    if pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT data FROM hypotheses ORDER BY created_at DESC LIMIT $1", limit
            )
            return [json.loads(r["data"]) for r in reversed(rows)]
    else:
        from pathlib import Path
        import os
        state = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
        path = state / "hypotheses.jsonl"
        if not path.exists():
            return []
        lines = [l for l in path.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
        return [json.loads(l) for l in lines[-limit:]]
