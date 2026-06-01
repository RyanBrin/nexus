"""Stock price adapter — yfinance for OHLCV data."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Optional

SCHEMA_VERSION = "1"


async def fetch(ticker: str) -> dict:
    """Fetch current price + OHLCV history for Elliott Wave analysis."""
    import yfinance as yf

    loop = asyncio.get_event_loop()

    def _fetch_sync():
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist_1d  = t.history(period="3mo",  interval="1d")
        hist_1h  = t.history(period="5d",   interval="1h")
        return info, hist_1d, hist_1h

    info, hist_1d, hist_1h = await loop.run_in_executor(None, _fetch_sync)

    price = float(info.last_price) if hasattr(info, "last_price") and info.last_price else None
    prev_close = float(info.previous_close) if hasattr(info, "previous_close") and info.previous_close else None
    daily_change_pct = ((price - prev_close) / prev_close * 100) if price and prev_close else None

    closes_1d = hist_1d["Close"].tolist() if not hist_1d.empty else []
    highs_1d  = hist_1d["High"].tolist()  if not hist_1d.empty else []
    lows_1d   = hist_1d["Low"].tolist()   if not hist_1d.empty else []
    closes_1h = hist_1h["Close"].tolist() if not hist_1h.empty else []

    return {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "price": price,
        "daily_change_pct": daily_change_pct,
        "closes_1d": closes_1d,
        "highs_1d":  highs_1d,
        "lows_1d":   lows_1d,
        "closes_1h": closes_1h,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
