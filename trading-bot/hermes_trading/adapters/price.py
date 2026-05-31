"""Price adapter — uses Kraken by default (no geo-restrictions)."""
import os
import ccxt.async_support as ccxt

SCHEMA_VERSION = "1"


class SchemaError(Exception):
    pass


async def fetch(asset: str = "BTC/USDT") -> dict:
    exchange_id = os.getenv("EXCHANGE_ID", "kraken")
    api_key = os.getenv("EXCHANGE_API_KEY", "")
    api_secret = os.getenv("EXCHANGE_API_SECRET", "")

    exchange_cls = getattr(ccxt, exchange_id)
    kwargs = {"enableRateLimit": True}
    if api_key:
        kwargs["apiKey"] = api_key
        kwargs["secret"] = api_secret

    # ccxt normalizes Kraken symbols — use BTC/USD (ccxt maps this to XXBTZUSD internally)
    kraken_asset = asset.replace("/USDT", "/USD") if exchange_id == "kraken" else asset

    exchange = exchange_cls(kwargs)
    try:
        await exchange.load_markets()
        ticker = await exchange.fetch_ticker(kraken_asset)
        ohlcv_1h  = await exchange.fetch_ohlcv(kraken_asset, timeframe="1h",  limit=50)
        ohlcv_15m = await exchange.fetch_ohlcv(kraken_asset, timeframe="15m", limit=60)
    finally:
        await exchange.close()

    result = {
        "schema_version": SCHEMA_VERSION,
        "asset": asset,
        "price": ticker["last"],
        "bid": ticker["bid"],
        "ask": ticker["ask"],
        "volume_24h": ticker["quoteVolume"],
        "closes_1h":  [c[4] for c in ohlcv_1h],
        "closes_15m": [c[4] for c in ohlcv_15m],
    }

    if result.get("schema_version") != SCHEMA_VERSION:
        raise SchemaError(f"price adapter schema mismatch: {result.get('schema_version')}")

    return result
