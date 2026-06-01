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
from hermes_trading.agents import risk_manager, news_agent, evaluator
from hermes_trading.trade_ideas import TradeIdea, append_idea, STATUS_APPROVED, STATUS_REJECTED, STATUS_WATCHING
from hermes_trading import agent_state
from hermes_trading import strategy_registry

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
    agent_state.mark_running()
    goals = _load_stock_goals()
    max_positions = goals.get("max_open_positions", MAX_OPEN_POSITIONS)
    stop_loss_pct = goals.get("default_stop_loss_pct", DEFAULT_STOP_LOSS_PCT)
    active_strategy = strategy_registry.get_active_strategy_name()
    news_api_key = os.getenv("NEWS_API_KEY", "")

    # Daily/weekly loss tracking (simple in-memory for paper trading)
    daily_pnl_pct = 0.0
    weekly_pnl_pct = 0.0

    while True:
        tick_start = datetime.now(timezone.utc)
        try:
            stocks = load_watchlist()
            active_strategy = strategy_registry.get_active_strategy_name()
            open_positions = [s.ticker for s in stocks if s.position_status == POSITION_IN_TRADE]
            open_count = len(open_positions)

            agent_state.mark_stock_scan([s.ticker for s in stocks])

            for stock in stocks:
                try:
                    market = await _fetch_stock_safe(stock.ticker)
                    if not market or not market.get("price"):
                        continue

                    price = market["price"]
                    change_pct = market.get("daily_change_pct") or 0.0

                    stock.current_price = price
                    stock.daily_change_pct = change_pct
                    stock.last_updated = tick_start.isoformat()

                    # 1. Elliott Wave analysis (always runs)
                    analysis = wave_strategy.analyze(stock.ticker, market, stop_loss_pct)

                    # 2. News agent (per-ticker)
                    news = await news_agent.analyze(stock.ticker, news_api_key)
                    has_earnings = news_agent.is_earnings_day(stock.ticker)

                    # 3. Evaluator — score the setup
                    setup = evaluator.evaluate(
                        ticker=stock.ticker,
                        wave_analysis=analysis,
                        news=news,
                        current_price=price,
                        strategy_version=active_strategy,
                        stop_loss_pct=stop_loss_pct,
                        has_earnings=has_earnings,
                    )

                    # 4. Claude interpretation
                    claude_notes = stock_reflect.reinterpret_with_claude(stock, analysis, market.get("closes_1d", []))

                    # Update watchlist entry with analysis
                    stock.signal = analysis.signal
                    stock.confidence_score = setup.confidence
                    stock.wave_count = analysis.wave_count
                    stock.fib_zone = analysis.fib_zone
                    stock.trend = analysis.trend
                    stock.risk_reward = str(setup.risk_reward)
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
                    elif stock.position_status != POSITION_IN_TRADE:

                        # Log every setup as a trade idea regardless of outcome
                        idea_status = STATUS_WATCHING
                        rejection_reason = ""
                        rm_decision = None

                        if setup.tradeable and stock.trading_enabled:
                            # 5. Risk Manager — final veto
                            rm_decision = risk_manager.evaluate(
                                ticker=stock.ticker,
                                direction=setup.direction,
                                entry_price=setup.entry_price,
                                stop_price=setup.stop_price,
                                target_price=setup.target_price,
                                confidence=setup.confidence,
                                open_positions=open_positions,
                                daily_pnl_pct=daily_pnl_pct,
                                weekly_pnl_pct=weekly_pnl_pct,
                                news_risk=setup.news_risk,
                                has_earnings_today=setup.has_earnings_today,
                            )

                            if rm_decision.approved:
                                idea_status = STATUS_APPROVED
                                stock.position_status = POSITION_IN_TRADE
                                stock.entry_price = setup.entry_price
                                stock.stop_loss_price = setup.stop_price
                                stock.take_profit_price = setup.target_price
                                open_positions.append(stock.ticker)
                                open_count += 1
                                log.info(f"Stock {stock.ticker} APPROVED @ ${price:.2f} | stop=${setup.stop_price:.2f} | target=${setup.target_price:.2f} | confidence={setup.confidence}")
                            else:
                                idea_status = STATUS_REJECTED
                                rejection_reason = rm_decision.reason
                                log.info(f"Stock {stock.ticker} BLOCKED by Risk Manager: {rm_decision.reason}")
                        elif not setup.tradeable:
                            idea_status = STATUS_REJECTED
                            rejection_reason = setup.not_tradeable_reason
                        elif not stock.trading_enabled:
                            idea_status = STATUS_WATCHING
                            rejection_reason = "trading_disabled_for_ticker"

                        # Log the trade idea with full context
                        append_idea(TradeIdea(
                            ticker=stock.ticker,
                            asset_type="stock",
                            direction=setup.direction,
                            entry_price=setup.entry_price,
                            stop_price=setup.stop_price,
                            target_price=setup.target_price,
                            risk_pct=rm_decision.risk_pct if rm_decision else None,
                            risk_reward=setup.risk_reward,
                            confidence=setup.confidence,
                            strategy_version=active_strategy,
                            chart_reason=setup.chart_reason,
                            wave_count=setup.wave_count,
                            fib_zone=setup.fib_zone,
                            trend=setup.trend,
                            news_summary=setup.news_summary,
                            news_risk=setup.news_risk,
                            status=idea_status,
                            rejection_reason=rejection_reason,
                            risk_checks_passed=rm_decision.checks_passed if rm_decision else [],
                            risk_checks_failed=rm_decision.checks_failed if rm_decision else [],
                            similar_past_setups="",
                            hermes_notes=claude_notes,
                        ))

                    elif stock.position_status == POSITION_EXITED:
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
