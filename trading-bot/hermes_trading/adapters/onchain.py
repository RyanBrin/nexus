"""On-chain adapter — free Glassnode community endpoints; override with API key."""
import os
import httpx

SCHEMA_VERSION = "1"


class SchemaError(Exception):
    pass


async def fetch() -> dict:
    api_key = os.getenv("GLASSNODE_API_KEY", "")
    headers = {"X-Api-Key": api_key} if api_key else {}

    # Free community metric: BTC exchange net position change
    url = "https://api.glassnode.com/v1/metrics/transactions/count"
    params = {"a": "BTC", "i": "24h"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            latest = data[-1] if data else {}
            tx_count = latest.get("v", 0)
    except Exception:
        tx_count = None  # non-fatal; loop continues without on-chain signal

    result = {
        "schema_version": SCHEMA_VERSION,
        "btc_tx_count_24h": tx_count,
    }

    if result.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError(f"onchain adapter schema mismatch: {result.get('schema_version')}")

    return result
