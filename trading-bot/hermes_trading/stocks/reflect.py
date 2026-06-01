"""Stock strategy reinterpretation — Claude AI explains every analysis decision."""
from __future__ import annotations
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from hermes_trading.stocks.strategy import WaveAnalysis
from hermes_trading.stocks.watchlist import StockEntry

log = logging.getLogger(__name__)
STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent.parent / "state"))


def _append_log(entry: dict) -> None:
    log_file = STATE / "stock_hypotheses.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({**entry, "ts": datetime.now(timezone.utc).isoformat()}) + "\n")


def load_stock_logs(limit: int = 50) -> list[dict]:
    log_file = STATE / "stock_hypotheses.jsonl"
    if not log_file.exists():
        return []
    try:
        lines = [l for l in log_file.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
        return [json.loads(l) for l in lines[-limit:]]
    except Exception:
        return []


def reinterpret_with_claude(stock: StockEntry, analysis: WaveAnalysis, recent_prices: list[float]) -> str:
    """Call Claude to generate a natural-language explanation of the current setup.
    Falls back to the deterministic reasoning string if API is unavailable."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return analysis.reasoning

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are Hermes, an AI swing trading analyst specializing in Elliott Wave Theory and Fibonacci analysis.

Analyze this stock setup and provide a concise trading interpretation in 2-3 sentences.
Be direct. State what you see, what you're waiting for, and why you would or wouldn't trade.

Stock: {stock.ticker} ({stock.company_name})
Current Price: ${stock.current_price:.2f}
Daily Change: {stock.daily_change_pct:+.2f}%
Trend: {analysis.trend}
Wave Count Estimate: {analysis.wave_count}
Fibonacci Zone: {analysis.fib_zone}
Signal: {analysis.signal}
Confidence: {analysis.confidence}/100
Swing High: ${analysis.swing_high:.2f if analysis.swing_high else 'n/a'}
Swing Low: ${analysis.swing_low:.2f if analysis.swing_low else 'n/a'}
Fib 38.2%: ${analysis.fib_38:.2f if analysis.fib_38 else 'n/a'}
Fib 50%: ${analysis.fib_50:.2f if analysis.fib_50 else 'n/a'}
Fib 61.8%: ${analysis.fib_62:.2f if analysis.fib_62 else 'n/a'}
Stop Loss: {analysis.stop_loss_pct}%
Risk/Reward: {analysis.risk_reward}
Trading Enabled: {stock.trading_enabled}

Write a short, sharp interpretation as Hermes would say it. Max 3 sentences."""

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    except Exception as e:
        log.warning(f"Claude stock reinterpretation failed for {stock.ticker}: {e}")
        return analysis.reasoning


def log_analysis(stock: StockEntry, analysis: WaveAnalysis, claude_notes: str) -> None:
    """Persist the full analysis to stock_hypotheses.jsonl."""
    _append_log({
        "symbol": stock.ticker,
        "asset_type": "stock",
        "company": stock.company_name,
        "price": stock.current_price,
        "trend": analysis.trend,
        "wave_count": analysis.wave_count,
        "fib_zone": analysis.fib_zone,
        "signal": analysis.signal,
        "confidence": analysis.confidence,
        "entry_plan": analysis.entry_plan,
        "stop_loss_pct": analysis.stop_loss_pct,
        "target": analysis.target_desc,
        "risk_reward": analysis.risk_reward,
        "reasoning": claude_notes,
        "trading_enabled": stock.trading_enabled,
    })
