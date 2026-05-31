"""Main trading loop — runs forever, one tick per minute."""
from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hermes_trading.adapters import price as price_adapter
from hermes_trading.adapters import onchain as onchain_adapter
from hermes_trading.adapters import news as news_adapter
from hermes_trading.adapters import macro as macro_adapter
from hermes_trading.score import score as compute_score
from hermes_trading import db

log = logging.getLogger(__name__)

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
CIRCUIT_BREAK_THRESHOLD = 5
TICK_SECONDS = 60


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


async def _load_trades() -> list[dict]:
    return await db.load_trades()


async def _append_trade(trade: dict) -> None:
    await db.append_trade(trade)


async def _write_heartbeat(status: str, failures: int, price: float | None = None, score: float | None = None, open_trade: dict | None = None) -> None:
    data = {
        "status": status,
        "last_tick": datetime.now(timezone.utc).isoformat(),
        "consecutive_failures": failures,
        "last_price": price,
        "last_score": score,
        "open_trade": open_trade,
    }
    await db.write_heartbeat(data)


def _consume_tv_signal() -> dict | None:
    path = STATE / "tv_signal.json"
    if not path.exists():
        return None
    try:
        signal = json.loads(path.read_text(encoding="utf-8-sig"))
        path.unlink()
        return signal
    except Exception:
        return None


async def _fetch_with_retry(adapter, label: str, *args, retries: int = 3) -> dict | None:
    delay = 2.0
    for attempt in range(retries):
        try:
            return await adapter.fetch(*args)
        except Exception as exc:
            log.warning(f"{label} fetch failed (attempt {attempt + 1}/{retries}): {exc}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
    return None


def _compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-(period + 1) + i] - closes[-(period + 1) + i - 1]
        (gains if diff > 0 else losses).append(abs(diff))
    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 1e-9
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _should_enter(strategy: dict, market: dict) -> bool:
    entry = strategy.get("entry", {})
    indicator = entry.get("indicator", "rsi")
    threshold = entry.get("threshold", 30)
    direction = entry.get("direction", "long")

    if indicator == "rsi":
        closes = market.get("closes_1h", [])
        rsi = _compute_rsi(closes)
        if rsi is None:
            return False
        if direction == "long":
            return rsi < threshold
        else:
            return rsi > threshold
    return False


async def run_loop(asset: str) -> None:
    consecutive_failures = 0
    open_trade: dict | None = None

    log.info(f"Booting hermes-trading worker — asset={asset} mode={os.getenv('HERMES_TRADING_MODE', 'paper')}")

    while True:
        tick_start = datetime.now(timezone.utc)

        try:
            strategy = _load_yaml(STATE / "strategy.yaml")
            goal = _load_yaml(STATE / "goal.yaml")

            price_data = await _fetch_with_retry(price_adapter, "price", asset)
            if price_data is None:
                raise RuntimeError("price adapter failed after retries")

            onchain_data = await _fetch_with_retry(onchain_adapter, "onchain")
            news_data = await _fetch_with_retry(news_adapter, "news")
            macro_data = await _fetch_with_retry(macro_adapter, "macro")

            market = {**(price_data or {}), **(onchain_data or {}), **(news_data or {}), **(macro_data or {})}
            current_price = price_data["price"]

            # Manage open trade
            if open_trade is not None:
                entry_price = open_trade["entry_price"]
                stop_loss_pct = strategy.get("stop_loss_pct", 2.0) / 100
                pnl_pct = (current_price - entry_price) / entry_price

                if pnl_pct <= -stop_loss_pct:
                    open_trade["exit_price"] = current_price
                    open_trade["pnl_pct"] = pnl_pct
                    open_trade["exit_ts"] = tick_start.isoformat()
                    open_trade["exit_reason"] = "stop_loss"
                    await _append_trade(open_trade)
                    log.info(f"Trade closed (stop loss): pnl={pnl_pct:.4f}")
                    open_trade = None
                else:
                    log.debug(f"Open trade pnl={pnl_pct:.4f}")

            # Check TradingView signal first (overrides RSI logic if present)
            tv = _consume_tv_signal()
            if tv:
                log.info(f"TradingView signal received: {tv['action']} @ {tv.get('price', current_price)}")
                if tv["action"] == "buy" and open_trade is None:
                    open_trade = {
                        "asset": asset,
                        "direction": "long",
                        "entry_price": tv.get("price") or current_price,
                        "entry_ts": tick_start.isoformat(),
                        "position_size_r": strategy.get("position_size_r", 0.5),
                        "strategy_version": strategy.get("version"),
                        "source": "tradingview",
                    }
                    log.info(f"Trade opened (TV signal): {asset} @ {open_trade['entry_price']}")
                elif tv["action"] in ("sell", "close") and open_trade is not None:
                    pnl_pct = (current_price - open_trade["entry_price"]) / open_trade["entry_price"]
                    open_trade["exit_price"] = current_price
                    open_trade["pnl_pct"] = pnl_pct
                    open_trade["exit_ts"] = tick_start.isoformat()
                    open_trade["exit_reason"] = "tradingview_signal"
                    await _append_trade(open_trade)
                    log.info(f"Trade closed (TV signal): pnl={pnl_pct:.4f}")
                    open_trade = None

            # RSI entry (only if no TV signal and no open trade)
            elif open_trade is None and _should_enter(strategy, market):
                position_size_r = strategy.get("position_size_r", 0.5)
                open_trade = {
                    "asset": asset,
                    "direction": strategy["entry"]["direction"],
                    "entry_price": current_price,
                    "entry_ts": tick_start.isoformat(),
                    "position_size_r": position_size_r,
                    "strategy_version": strategy.get("version"),
                    "source": "rsi",
                }
                log.info(f"Trade opened (RSI): {asset} @ {current_price}")

            trades = await _load_trades()
            s = compute_score(trades, goal)
            log.info(f"tick score={s:.3f} price={current_price} open_trade={open_trade is not None}")

            consecutive_failures = 0
            await _write_heartbeat("running", 0, price=current_price, score=s, open_trade=open_trade)

        except Exception as exc:
            consecutive_failures += 1
            log.error(f"tick failed ({consecutive_failures}/{CIRCUIT_BREAK_THRESHOLD}): {exc}")
            await _write_heartbeat("error", consecutive_failures, open_trade=open_trade)

            if consecutive_failures >= CIRCUIT_BREAK_THRESHOLD:
                log.critical("Circuit breaker tripped — halting loop.")
                raise SystemExit(1)

        elapsed = (datetime.now(timezone.utc) - tick_start).total_seconds()
        await asyncio.sleep(max(0, TICK_SECONDS - elapsed))
