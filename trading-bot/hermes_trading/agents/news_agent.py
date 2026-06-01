"""Per-ticker news sentiment agent.

Filters trades on news risk. News is a FILTER, not the primary trigger.
Blocks: earnings days, lawsuits, major announcements, high-risk macro events.
"""
from __future__ import annotations
import asyncio
import os
from datetime import datetime, timezone

RISK_NORMAL   = "normal"
RISK_ELEVATED = "elevated"
RISK_HIGH     = "high"


async def analyze(ticker: str, api_key: str = "") -> dict:
    """Fetch and classify recent news for a ticker. Returns risk assessment."""
    if not api_key:
        api_key = os.getenv("NEWS_API_KEY", "")

    result = {
        "ticker": ticker,
        "risk_level": RISK_NORMAL,
        "sentiment": "neutral",
        "headline_count": 0,
        "headlines": [],
        "flags": [],
        "summary": "No news data available.",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    if not api_key:
        result["summary"] = "NEWS_API_KEY not set — news filter disabled."
        return result

    try:
        import httpx
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": api_key,
            "language": "en",
        }
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])

        headlines = [a.get("title", "") for a in articles if a.get("title")]
        result["headline_count"] = len(headlines)
        result["headlines"] = headlines[:5]

        # Keyword classification
        pos_words = {"buy", "upgrade", "beat", "surge", "record", "rally", "bullish", "strong"}
        neg_words = {"sell", "downgrade", "miss", "crash", "lawsuit", "fraud", "loss", "bearish", "weak"}
        risk_words = {"earnings", "sec", "investigation", "bankruptcy", "lawsuit", "recall",
                      "fda", "regulatory", "delisted", "halt", "suspended"}

        all_text = " ".join(headlines).lower()

        pos_count = sum(1 for w in pos_words if w in all_text)
        neg_count = sum(1 for w in neg_words if w in all_text)
        risk_count = sum(1 for w in risk_words if w in all_text)

        flags = [w for w in risk_words if w in all_text]
        result["flags"] = flags

        # Risk classification
        if risk_count >= 2 or "earnings" in all_text:
            result["risk_level"] = RISK_HIGH
            result["summary"] = f"HIGH RISK: Found {risk_count} risk keywords: {', '.join(flags[:3])}"
        elif risk_count >= 1 or neg_count > pos_count:
            result["risk_level"] = RISK_ELEVATED
            result["summary"] = f"Elevated risk. Flags: {', '.join(flags) or 'negative sentiment'}."
        else:
            result["risk_level"] = RISK_NORMAL

        # Sentiment
        if pos_count > neg_count:
            result["sentiment"] = "bullish"
        elif neg_count > pos_count:
            result["sentiment"] = "bearish"
        else:
            result["sentiment"] = "neutral"

        if result["risk_level"] == RISK_NORMAL:
            result["summary"] = (f"Sentiment: {result['sentiment']}. "
                                  f"{pos_count} positive, {neg_count} negative signals.")

    except Exception as e:
        result["summary"] = f"News fetch failed: {e}"
        result["risk_level"] = RISK_NORMAL  # don't block on API failure

    return result


def is_earnings_day(ticker: str) -> bool:
    """Check if today is an earnings day. Returns False if data unavailable."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        cal = t.calendar
        if cal is None or cal.empty:
            return False
        today = datetime.now().strftime("%Y-%m-%d")
        earnings_dates = cal.T.get("Earnings Date", [])
        return any(str(d)[:10] == today for d in earnings_dates)
    except Exception:
        return False
