"""Strategy Evaluator — scores setups and decides if they meet the bar.

Takes output from the Market Scanner (Elliott Wave analysis) and the News Agent,
combines them into a final score and entry plan, then passes to the Risk Manager.

Does NOT place trades. Does NOT touch the Risk Manager.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from hermes_trading.stocks.strategy import WaveAnalysis
from hermes_trading.agents.news_agent import RISK_NORMAL, RISK_ELEVATED, RISK_HIGH


@dataclass
class EvaluatedSetup:
    ticker: str
    direction: str
    entry_price: float
    stop_price: float
    target_price: float
    confidence: int            # 0-100 composite
    risk_reward: float
    strategy_version: str
    chart_reason: str
    news_summary: str
    news_risk: str
    wave_count: str
    fib_zone: str
    trend: str
    has_earnings_today: bool
    setup_type: str            # "fib_retracement" / "trend_continuation" / "no_setup"
    tradeable: bool            # False = not even worth sending to Risk Manager
    not_tradeable_reason: str  # why if not tradeable


def evaluate(
    ticker: str,
    wave_analysis: WaveAnalysis,
    news: dict,
    current_price: float,
    strategy_version: str,
    stop_loss_pct: float = 1.5,
    has_earnings: bool = False,
) -> EvaluatedSetup:
    """Combine chart + news into a scored, evaluated setup."""

    from hermes_trading.stocks.watchlist import (
        SIGNAL_ENTRY, SIGNAL_WAVE_2, SIGNAL_WAVE_4,
        SIGNAL_INVALIDATED, SIGNAL_NO_SETUP
    )

    news_risk = news.get("risk_level", RISK_NORMAL)
    news_summary = news.get("summary", "")
    chart_reason = wave_analysis.entry_plan

    # Start with Elliott Wave confidence
    confidence = wave_analysis.confidence

    # News adjustments
    if news_risk == RISK_HIGH:
        confidence = max(0, confidence - 25)
        chart_reason = f"[NEWS HIGH RISK] {chart_reason}"
    elif news_risk == RISK_ELEVATED:
        confidence = max(0, confidence - 10)

    # Earnings penalty
    if has_earnings:
        confidence = max(0, confidence - 40)

    # Determine if tradeable at all
    tradeable = True
    not_tradeable_reason = ""

    if wave_analysis.signal in (SIGNAL_INVALIDATED, SIGNAL_NO_SETUP):
        tradeable = False
        not_tradeable_reason = f"Elliott Wave signal: {wave_analysis.signal}"
    elif confidence < 40:
        tradeable = False
        not_tradeable_reason = f"Confidence too low: {confidence}/100"
    elif news_risk == RISK_HIGH:
        tradeable = False
        not_tradeable_reason = f"High news risk: {news_summary[:80]}"
    elif has_earnings:
        tradeable = False
        not_tradeable_reason = "Earnings day — no trades"

    # Calculate prices
    stop_price = round(current_price * (1 - stop_loss_pct / 100), 2)
    target_price = wave_analysis.swing_high if wave_analysis.swing_high else round(current_price * 1.04, 2)

    # R/R calculation
    risk = current_price - stop_price
    reward = target_price - current_price
    rr = round(reward / risk, 2) if risk > 0 else 0

    # Setup type classification
    if wave_analysis.signal in (SIGNAL_WAVE_2, SIGNAL_WAVE_4):
        setup_type = "fib_retracement"
    elif wave_analysis.trend in ("bullish", "bearish") and wave_analysis.signal == SIGNAL_ENTRY:
        setup_type = "trend_continuation"
    else:
        setup_type = "no_clear_setup"

    return EvaluatedSetup(
        ticker=ticker,
        direction="long" if wave_analysis.trend != "bearish" else "short",
        entry_price=current_price,
        stop_price=stop_price,
        target_price=target_price,
        confidence=confidence,
        risk_reward=rr,
        strategy_version=strategy_version,
        chart_reason=chart_reason,
        news_summary=news_summary,
        news_risk=news_risk,
        wave_count=wave_analysis.wave_count,
        fib_zone=wave_analysis.fib_zone,
        trend=wave_analysis.trend,
        has_earnings_today=has_earnings,
        setup_type=setup_type,
        tradeable=tradeable,
        not_tradeable_reason=not_tradeable_reason,
    )
