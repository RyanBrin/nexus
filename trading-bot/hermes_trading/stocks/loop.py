"""Stock trading loop — runs alongside the BTC loop.

Scans each ticker in the watchlist every TICK_SECONDS.
For tickers with trading_enabled=True, applies Elliott Wave + Fib strategy
and manages paper positions. BTC loop is never imported or touched here.
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from hermes_trading.adapters import stock_price as stock_price_adapter
from hermes_trading.stocks import strategy as wave_strategy
from hermes_trading.stocks import reflect as stock_reflect
from hermes_trading.stocks.watchlist import (
    load_watchlist, upsert_stock, StockEntry,
    POSITION_IN_TRADE, POSITION_EXITED, POSITION_WATCHING, POSITION_NO_POS,
    SIGNAL_ENTRY, SIGNAL_INVALIDATED, SIGNAL_EXIT
)

log = logging.getLogger(__name__)

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent.parent / "state"))

# Risk settings — can be overridden via stock_goals.yaml
MAX_OPEN_POSITIONS = 3
MAX_RISK_PER_TRADE_PCT = 2.0
DEFAULT_STOP_LOSS_PCT = 1.5
TICK_SECONDS = 300   # 5-minute scan cycle for stocks (markets move slower than crypto)


def _load_stock_goals() -> dict:
    goals_file = STATE / "stock_goals.yaml"
    if not goals_file.exists():
        return {}
    try:
        import yaml
        with open(goals_file) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _append_stock_trade(trade: dict) -> None:
    trade_file = STATE / "stock_trades.jsonl"
    with open(trade_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(trade) + "\n")


def _load_stock_trades(limit: int = 200) -> list[dict]:
    trade_file = STATE / "stock_trades.jsonl"
    if not trade_file.exists():
        return []
    try:
        lines = [l for l in trade_file.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
        return [json.loads(l) for l in lines[-limit:]]
    except Exception:
        return []


def _count_open_positions(stocks: list[StockEntry]) -> int:
    return sum(1 for s in stocks if s.position_status == POSITION_IN_TRADE)


async def _fetch_stock_safe(ticker: str) -> dict | None:
    try:
        return await stock_price_adapter.fetch(ticker)
    except Exception as exc:
        log.warning(f"Stock price fetch failed for {ticker}: {exc}")
        return None


async def run_stock_loop() -> None:
    log.info("Stock trading loop started.")
    goals = _load_stock_goals()
    max_positions = goals.get("max_open_positions", MAX_OPEN_POSITIONS)
    max_risk = goals.get("max_risk_per_trade_pct", MAX_RISK_PER_TRADE_PCT)
    stop_loss_pct = goals.get("default_stop_loss_pct", DEFAULT_STOP_LOSS_PCT)

    while True:
        tick_start = datetime.now(timezone.utc)
        try:
            stocks = load_watchlist()
            open_count = _count_open_positions(stocks)

            for stock in stocks:
                try:
                    market = await _fetch_stock_safe(stock.ticker)
                    if not market or not market.get("price"):
                        continue

                    price = market["price"]
                    change_pct = market.get("daily_change_pct") or 0.0

                    # Update price on watchlist entry
                    stock.current_price = price
                    stock.daily_change_pct = change_pct
                    stock.last_updated = tick_start.isoformat()

                    # Run Elliott Wave analysis regardless of trading toggle
                    analysis = wave_strategy.analyze(stock.ticker, market, stop_loss_pct)

                    # Get Claude interpretation (uses Haiku, cheap)
                    claude_notes = stock_reflect.reinterpret_with_claude(stock, analysis, market.get("closes_1d", []))

                    # Update stock with analysis results
                    stock.signal = analysis.signal
                    stock.confidence_score = analysis.confidence
                    stock.wave_count = analysis.wave_count
                    stock.fib_zone = analysis.fib_zone
                    stock.trend = analysis.trend
                    stock.risk_reward = analysis.risk_reward
                    stock.hermes_notes = claude_notes

                    # --- Manage existing position ---
                    if stock.position_status == POSITION_IN_TRADE and stock.entry_price:
                        pnl_pct = (price - stock.entry_price) / stock.entry_price

                        # Stop loss hit
                        if pnl_pct <= -(stop_loss_pct / 100):
                            stock.position_status = POSITION_EXITED
                            _append_stock_trade({
                                "ticker": stock.ticker,
                                "direction": "long",
                                "entry_price": stock.entry_price,
                                "exit_price": price,
                                "pnl_pct": pnl_pct,
                                "exit_reason": "stop_loss",
                                "entry_ts": stock.last_updated,
                                "exit_ts": tick_start.isoformat(),
                                "asset_type": "stock",
                                "wave_count": stock.wave_count,
                                "confidence": stock.confidence_score,
                            })
                            log.info(f"Stock {stock.ticker} stop loss hit: pnl={pnl_pct:.3f}")
                            stock.entry_price = None
                            stock.stop_loss_price = None
                            stock.take_profit_price = None
                            open_count -= 1

                        # Take profit (RSI-equivalent: signal flips to invalidated/exit or hits target)
                        elif (analysis.signal == SIGNAL_INVALIDATED or
                              (stock.take_profit_price and price >= stock.take_profit_price)):
                            stock.position_status = POSITION_EXITED
                            _append_stock_trade({
                                "ticker": stock.ticker,
                                "direction": "long",
                                "entry_price": stock.entry_price,
                                "exit_price": price,
                                "pnl_pct": pnl_pct,
                                "exit_reason": "take_profit",
                                "entry_ts": stock.last_updated,
                                "exit_ts": tick_start.isoformat(),
                                "asset_type": "stock",
                                "wave_count": stock.wave_count,
                                "confidence": stock.confidence_score,
                            })
                            log.info(f"Stock {stock.ticker} take profit: pnl={pnl_pct:.3f}")
                            stock.entry_price = None
                            stock.stop_loss_price = None
                            stock.take_profit_price = None
                            open_count -= 1

                    # --- Consider new entry ---
                    elif (stock.trading_enabled
                          and stock.position_status != POSITION_IN_TRADE
                          and analysis.signal == SIGNAL_ENTRY
                          and analysis.confidence >= 65
                          and open_count < max_positions):

                        stop_price = price * (1 - stop_loss_pct / 100)
                        target_price = analysis.swing_high if analysis.swing_high else price * 1.04

                        stock.position_status = POSITION_IN_TRADE
                        stock.entry_price = price
                        stock.stop_loss_price = stop_price
                        stock.take_profit_price = target_price
                        open_count += 1
                        log.info(f"Stock {stock.ticker} entry @ ${price:.2f} | stop=${stop_price:.2f} | target=${target_price:.2f}")

                    elif stock.position_status == POSITION_EXITED:
                        # Reset to watching after 1 cycle
                        stock.position_status = POSITION_WATCHING

                    # Log analysis to hypotheses file
                    stock_reflect.log_analysis(stock, analysis, claude_notes)
                    upsert_stock(stock)

                except Exception as exc:
                    log.error(f"Error processing stock {stock.ticker}: {exc}")
                    continue

        except Exception as exc:
            log.error(f"Stock loop tick failed: {exc}")

        elapsed = (datetime.now(timezone.utc) - tick_start).total_seconds()
        await asyncio.sleep(max(0, TICK_SECONDS - elapsed))
