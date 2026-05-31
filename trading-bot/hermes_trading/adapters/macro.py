"""Macro adapter — pulls DXY and 10y yield from Yahoo Finance (free, no key needed)."""
import httpx

SCHEMA_VERSION = "1"


class SchemaError(Exception):
    pass


async def fetch() -> dict:
    results = {}
    tickers = {"dxy": "DX-Y.NYB", "us10y": "^TNX"}

    async with httpx.AsyncClient(timeout=10) as client:
        for name, symbol in tickers.items():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                data = resp.json()
                price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                results[name] = price
            except Exception:
                results[name] = None  # non-fatal

    result = {
        "schema_version": SCHEMA_VERSION,
        "dxy": results.get("dxy"),
        "us10y_yield": results.get("us10y"),
    }

    if result.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError(f"macro adapter schema mismatch: {result.get('schema_version')}")

    return result
