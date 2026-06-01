"""Elliott Wave + Fibonacci swing-trading strategy for stocks.

Approach:
1. Detect recent swing highs/lows from daily closes
2. Identify the dominant trend (bullish/bearish/unclear)
3. Calculate Fibonacci retracement zones from the last impulse move
4. Check if current price is in a high-probability entry zone (38.2% - 61.8%)
5. Estimate wave position heuristically
6. Generate signal + confidence score + reasoning

This is a heuristic implementation — not a full wave-counting engine.
Confidence is gated at several checkpoints so the bot won't force trades
on unclear setups.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


FIBO_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]
ENTRY_ZONE_LOW  = 0.382
ENTRY_ZONE_HIGH = 0.618

# Minimum candles needed for a meaningful analysis
MIN_CANDLES = 20
# Minimum impulse move size (% of price) to be worth trading
MIN_IMPULSE_PCT = 0.03   # 3% move needed


@dataclass
class WaveAnalysis:
    ticker: str
    trend: str              # bullish / bearish / unclear
    wave_count: str         # e.g. "possible wave 2 pullback"
    fib_zone: str           # e.g. "0.382–0.618 retracement"
    signal: str             # from watchlist signal constants
    confidence: int         # 0–100
    entry_plan: str
    stop_loss_pct: float    # e.g. 1.5
    target_desc: str
    risk_reward: str
    reasoning: str
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
    fib_38: Optional[float] = None
    fib_50: Optional[float] = None
    fib_62: Optional[float] = None


def _find_swing_points(closes: list[float], highs: list[float], lows: list[float],
                       lookback: int = 5) -> tuple[float, float, int, int]:
    """Return (swing_high, swing_low, high_idx, low_idx) over last `lookback` bars."""
    window_h = highs[-lookback:] if highs else closes[-lookback:]
    window_l = lows[-lookback:]  if lows  else closes[-lookback:]
    swing_high = max(window_h)
    swing_low  = min(window_l)
    high_idx   = len(highs) - lookback + window_h.index(swing_high)
    low_idx    = len(lows)  - lookback + window_l.index(swing_low)
    return swing_high, swing_low, high_idx, low_idx


def _fib_retrace(high: float, low: float, level: float, bullish: bool) -> float:
    """Price at a given Fibonacci retracement level."""
    if bullish:
        # Retracing down from high
        return high - (high - low) * level
    else:
        # Retracing up from low
        return low + (high - low) * level


def _count_alternations(closes: list[float], window: int = 30) -> int:
    """Count direction changes (up→down or down→up) in recent closes."""
    recent = closes[-window:]
    changes = 0
    for i in range(1, len(recent)):
        if (recent[i] > recent[i-1]) != (recent[i-1] > recent[i-2] if i > 1 else True):
            changes += 1
    return changes


def analyze(ticker: str, market_data: dict, stop_loss_pct: float = 1.5) -> WaveAnalysis:
    """Run Elliott Wave + Fib analysis. Returns WaveAnalysis regardless of outcome."""
    from hermes_trading.stocks.watchlist import (
        SIGNAL_NO_SETUP, SIGNAL_TREND_UNCLEAR, SIGNAL_WAITING_RETRACE,
        SIGNAL_WAVE_2, SIGNAL_WAVE_4, SIGNAL_INVALIDATED, SIGNAL_ENTRY, SIGNAL_WATCHING
    )

    closes = market_data.get("closes_1d", [])
    highs  = market_data.get("highs_1d", closes)
    lows   = market_data.get("lows_1d", closes)
    price  = market_data.get("price")

    # --- Guard: not enough data ---
    if len(closes) < MIN_CANDLES or not price:
        return WaveAnalysis(
            ticker=ticker, trend="unclear", wave_count="insufficient data",
            fib_zone="n/a", signal=SIGNAL_NO_SETUP, confidence=0,
            entry_plan="Waiting for more price history.",
            stop_loss_pct=stop_loss_pct, target_desc="n/a", risk_reward="n/a",
            reasoning="Not enough candles to form a valid Elliott Wave setup."
        )

    # --- Step 1: Trend via 20-day vs 50-day SMA ---
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sum(closes) / len(closes)
    price_above_sma20 = price > sma20
    sma_bullish = sma20 > sma50

    if sma_bullish and price_above_sma20:
        trend = "bullish"
    elif not sma_bullish and not price_above_sma20:
        trend = "bearish"
    else:
        trend = "unclear"

    # --- Step 2: Find swing points over last 30 days ---
    lookback = min(30, len(closes))
    swing_high, swing_low, high_idx, low_idx = _find_swing_points(closes, highs, lows, lookback)
    impulse_size = (swing_high - swing_low) / swing_low

    # --- Guard: impulse too small to trade ---
    if impulse_size < MIN_IMPULSE_PCT:
        return WaveAnalysis(
            ticker=ticker, trend=trend, wave_count="no impulse detected",
            fib_zone="n/a", signal=SIGNAL_WAITING_RETRACE, confidence=10,
            entry_plan="Waiting for a meaningful impulse move to set up retracement.",
            stop_loss_pct=stop_loss_pct, target_desc="n/a", risk_reward="n/a",
            reasoning=f"Impulse move of {impulse_size*100:.1f}% is too small (min {MIN_IMPULSE_PCT*100:.0f}%). "
                      "No valid wave structure to trade."
        )

    # --- Step 3: Fibonacci retracement levels ---
    bullish_impulse = high_idx > low_idx   # high came AFTER low = bullish impulse
    f38 = _fib_retrace(swing_high, swing_low, 0.382, bullish_impulse)
    f50 = _fib_retrace(swing_high, swing_low, 0.500, bullish_impulse)
    f62 = _fib_retrace(swing_high, swing_low, 0.618, bullish_impulse)
    f79 = _fib_retrace(swing_high, swing_low, 0.786, bullish_impulse)

    # --- Step 4: Where is current price relative to fib zone? ---
    in_entry_zone = False
    zone_label = "outside retracement zone"

    if bullish_impulse:
        # Bullish: price retracing DOWN into support zone
        if f62 <= price <= f38:
            in_entry_zone = True
            zone_label = f"0.382–0.618 retracement ({f38:.2f}–{f62:.2f})"
        elif price < f79:
            zone_label = f"below 0.786 ({f79:.2f}) — setup potentially invalidated"
        elif price > swing_high:
            zone_label = "above swing high — possible breakout / wave 3 continuation"
        else:
            zone_label = f"above 0.382 ({f38:.2f}) — not yet in retracement zone"
    else:
        # Bearish: price retracing UP into resistance zone
        if f38 <= price <= f62:
            in_entry_zone = True
            zone_label = f"0.382–0.618 retracement ({f38:.2f}–{f62:.2f})"
        elif price > f79:
            zone_label = f"above 0.786 ({f79:.2f}) — bearish setup potentially invalidated"
        else:
            zone_label = f"below 0.382 ({f38:.2f}) — not yet in retracement zone"

    # --- Step 5: Wave count heuristic ---
    alternations = _count_alternations(closes)
    # Rough heuristic: even alternation count suggests corrective wave
    if alternations % 2 == 0 and in_entry_zone:
        wave_guess = "possible wave 2 pullback" if bullish_impulse else "possible wave B correction"
        wave_signal = SIGNAL_WAVE_2
    elif alternations % 2 == 1 and in_entry_zone:
        wave_guess = "possible wave 4 correction" if bullish_impulse else "possible wave 4"
        wave_signal = SIGNAL_WAVE_4
    elif price > swing_high and bullish_impulse:
        wave_guess = "possible wave 3 breakout in progress"
        wave_signal = SIGNAL_WATCHING
    else:
        wave_guess = "wave count unclear"
        wave_signal = SIGNAL_TREND_UNCLEAR if trend == "unclear" else SIGNAL_WAITING_RETRACE

    # --- Step 6: Confidence scoring ---
    confidence = 0

    # Trend alignment: up to 25 pts
    if trend == "bullish" and bullish_impulse:
        confidence += 25
    elif trend == "bearish" and not bullish_impulse:
        confidence += 25
    elif trend != "unclear":
        confidence += 10

    # In Fibonacci entry zone: up to 35 pts
    if in_entry_zone:
        confidence += 35
    elif zone_label.startswith("above swing high") or zone_label.startswith("below swing high"):
        confidence += 5

    # Impulse size bonus: up to 20 pts
    if impulse_size >= 0.08:
        confidence += 20
    elif impulse_size >= 0.05:
        confidence += 12
    elif impulse_size >= 0.03:
        confidence += 6

    # Wave alignment: up to 20 pts
    if wave_signal in (SIGNAL_WAVE_2, SIGNAL_WAVE_4) and in_entry_zone:
        confidence += 20

    confidence = min(100, confidence)

    # --- Step 7: Signal decision ---
    if confidence >= 70 and in_entry_zone and trend != "unclear":
        signal = SIGNAL_ENTRY
    elif confidence >= 45 and in_entry_zone:
        signal = wave_signal
    elif trend == "unclear":
        signal = SIGNAL_TREND_UNCLEAR
    elif price < f79 and bullish_impulse:
        signal = SIGNAL_INVALIDATED
    else:
        signal = SIGNAL_WAITING_RETRACE

    # --- Step 8: Entry plan + risk/reward ---
    rr_ratio = round((impulse_size * 100) / stop_loss_pct, 1)
    rr_str = f"{rr_ratio}R" if rr_ratio > 0 else "n/a"

    if signal == SIGNAL_ENTRY:
        entry_plan = (f"{'Bullish' if bullish_impulse else 'Bearish'} entry in Fibonacci zone "
                      f"({f38:.2f}–{f62:.2f}). Wait for a bullish candle confirmation.")
    elif signal == SIGNAL_INVALIDATED:
        entry_plan = f"Setup invalidated — price broke below 0.786 ({f79:.2f}). Do not enter."
    else:
        entry_plan = (f"Waiting for price to reach retracement zone "
                      f"({f38:.2f}–{f62:.2f}) before considering entry.")

    target_desc = f"Prior {'high' if bullish_impulse else 'low'} at ${swing_high if bullish_impulse else swing_low:.2f} or Fibonacci extension"

    reasoning = (
        f"{'Bullish' if bullish_impulse else 'Bearish'} impulse of {impulse_size*100:.1f}% detected "
        f"(${swing_low:.2f} → ${swing_high:.2f}). "
        f"Trend: {trend} (SMA20={sma20:.2f}, SMA50={sma50:.2f}). "
        f"Current price ${price:.2f} is {zone_label}. "
        f"{wave_guess.capitalize()}. "
        f"Confidence: {confidence}/100."
    )

    return WaveAnalysis(
        ticker=ticker,
        trend=trend,
        wave_count=wave_guess,
        fib_zone=zone_label,
        signal=signal,
        confidence=confidence,
        entry_plan=entry_plan,
        stop_loss_pct=stop_loss_pct,
        target_desc=target_desc,
        risk_reward=rr_str,
        reasoning=reasoning,
        swing_high=swing_high,
        swing_low=swing_low,
        fib_38=f38,
        fib_50=f50,
        fib_62=f62,
    )
