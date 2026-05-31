"""News adapter — free NewsAPI endpoint; override with API key for higher limits."""
import os
import httpx

SCHEMA_VERSION = "1"


class SchemaError(Exception):
    pass


async def fetch() -> dict:
    api_key = os.getenv("NEWS_API_KEY", "")
    sentiment = None

    if api_key:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": "bitcoin OR BTC",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                articles = resp.json().get("articles", [])
                # naive positive/negative keyword count
                pos_words = {"surge", "rally", "bullish", "gain", "up", "high", "record"}
                neg_words = {"crash", "drop", "bearish", "loss", "down", "low", "ban"}
                pos = sum(
                    1 for a in articles
                    for w in pos_words
                    if w in (a.get("title") or "").lower()
                )
                neg = sum(
                    1 for a in articles
                    for w in neg_words
                    if w in (a.get("title") or "").lower()
                )
                sentiment = (pos - neg) / max(len(articles), 1)
        except Exception:
            sentiment = None

    result = {
        "schema_version": SCHEMA_VERSION,
        "headline_sentiment": sentiment,  # None if no key / fetch failed
    }

    if result.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError(f"news adapter schema mismatch: {result.get('schema_version')}")

    return result
