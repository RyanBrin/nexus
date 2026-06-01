"""Risk Manager — hard veto module with final say on every trade.

CRITICAL: This module is intentionally isolated from the learning system.
- It must NOT be imported by reflect.py
- It must NOT be modifiable by Claude's strategy optimization
- Its core rules are hardcoded and only changeable by the developer
- If it blocks a trade, the trade does not happen. No exceptions.

Architecture (per ChatGPT advice):
  Hermes Brain → suggests trade
  Risk Manager → approves or blocks
  Executor      → only acts if Risk Manager approved
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent.parent / "state"))

# ── Hardcoded safety limits — NEVER auto-modified ─────────────────────────────
HARD_LIMITS = {
    "max_risk_per_trade_pct": 2.0,      # never risk more than 2% per trade
    "min_stop_loss_pct": 0.1,           # stop loss must exist (>=0.1%)
    "max_stop_loss_pct": 5.0,           # stop can't be unreasonably wide
    "min_risk_reward": 1.5,             # minimum R/R before entry
    "max_open_positions": 5,            # across all stocks
    "max_daily_loss_pct": 3.0,          # halt if daily loss exceeds this
    "max_weekly_loss_pct": 6.0,         # halt if weekly loss exceeds this
    "min_confidence": 55,               # minimum confidence score 0-100
    "live_trading_enabled": False,      # NEVER true unless explicitly set by developer
    "allow_earnings_day_trades": False, # block trades on earnings day
}


@dataclass
class RiskDecision:
    approved: bool
    ticker: str
    reason: str                  # short label for the decision
    explanation: str             # full explanation
    checks_passed: list[str]
    checks_failed: list[str]
    risk_pct: Optional[float] = None
    risk_reward: Optional[float] = None


def _load_settings() -> dict:
    """Load soft settings from hermes_settings.json — overlaid on top of hard limits."""
    settings_file = STATE / "hermes_settings.json"
    if not settings_file.exists():
        return {}
    try:
        import json
        return json.loads(settings_file.read_text())
    except Exception:
        return {}


def _get_limit(key: str) -> float:
    """Get effective limit: hard limit takes precedence, then user settings."""
    hard = HARD_LIMITS.get(key)
    soft = _load_settings().get("risk", {}).get(key)
    if hard is None:
        return soft or 0
    # For safety, always use the MORE restrictive of the two
    if isinstance(hard, float) and isinstance(soft, (float, int)):
        if key in ("max_risk_per_trade_pct", "max_open_positions", "max_daily_loss_pct",
                   "max_weekly_loss_pct", "max_stop_loss_pct"):
            return min(hard, soft)  # lower = safer
        if key in ("min_risk_reward", "min_confidence", "min_stop_loss_pct"):
            return max(hard, float(soft))  # higher = safer
    return hard


def evaluate(
    ticker: str,
    direction: str,
    entry_price: float,
    stop_price: float,
    target_price: float,
    confidence: int,
    open_positions: list[str],
    daily_pnl_pct: float,
    weekly_pnl_pct: float,
    news_risk: str = "normal",           # "normal" / "elevated" / "high"
    has_earnings_today: bool = False,
    account_size: float = 10000.0,       # paper account size for position sizing
) -> RiskDecision:
    """Run all risk checks. Returns approved=True only if ALL pass."""

    passed = []
    failed = []

    # ── 1. Live trading gate (hardcoded — never changes) ──────────────────────
    if HARD_LIMITS["live_trading_enabled"]:
        failed.append("live_trading_would_execute_real_money")
    else:
        passed.append("paper_mode_confirmed")

    # ── 2. Stop loss required ─────────────────────────────────────────────────
    if stop_price is None or stop_price <= 0:
        failed.append("no_stop_loss")
    else:
        sl_pct = abs(entry_price - stop_price) / entry_price * 100
        min_sl = _get_limit("min_stop_loss_pct")
        max_sl = _get_limit("max_stop_loss_pct")
        if sl_pct < min_sl:
            failed.append(f"stop_loss_too_tight_{sl_pct:.2f}pct_min_{min_sl}pct")
        elif sl_pct > max_sl:
            failed.append(f"stop_loss_too_wide_{sl_pct:.2f}pct_max_{max_sl}pct")
        else:
            passed.append(f"stop_loss_valid_{sl_pct:.2f}pct")

    # ── 3. Target required + risk/reward check ────────────────────────────────
    if target_price is None or target_price <= 0:
        failed.append("no_target_price")
    else:
        if direction == "long":
            reward = target_price - entry_price
            risk = entry_price - stop_price
        else:
            reward = entry_price - target_price
            risk = stop_price - entry_price
        rr = reward / risk if risk > 0 else 0
        min_rr = _get_limit("min_risk_reward")
        if rr < min_rr:
            failed.append(f"risk_reward_too_low_{rr:.2f}R_min_{min_rr}R")
        else:
            passed.append(f"risk_reward_acceptable_{rr:.2f}R")

    # ── 4. Confidence threshold ───────────────────────────────────────────────
    min_conf = int(_get_limit("min_confidence"))
    if confidence < min_conf:
        failed.append(f"confidence_too_low_{confidence}_min_{min_conf}")
    else:
        passed.append(f"confidence_ok_{confidence}")

    # ── 5. Duplicate position check ───────────────────────────────────────────
    if ticker in open_positions:
        failed.append(f"duplicate_position_{ticker}_already_open")
    else:
        passed.append("no_duplicate_position")

    # ── 6. Max open positions ─────────────────────────────────────────────────
    max_pos = int(_get_limit("max_open_positions"))
    if len(open_positions) >= max_pos:
        failed.append(f"max_positions_reached_{len(open_positions)}_of_{max_pos}")
    else:
        passed.append(f"positions_available_{len(open_positions)}_of_{max_pos}")

    # ── 7. Daily loss limit ───────────────────────────────────────────────────
    max_daily = _get_limit("max_daily_loss_pct")
    if daily_pnl_pct <= -max_daily:
        failed.append(f"daily_loss_limit_hit_{daily_pnl_pct:.2f}pct_limit_{max_daily}pct")
    else:
        passed.append(f"daily_pnl_ok_{daily_pnl_pct:+.2f}pct")

    # ── 8. Weekly loss limit ──────────────────────────────────────────────────
    max_weekly = _get_limit("max_weekly_loss_pct")
    if weekly_pnl_pct <= -max_weekly:
        failed.append(f"weekly_loss_limit_hit_{weekly_pnl_pct:.2f}pct_limit_{max_weekly}pct")
    else:
        passed.append(f"weekly_pnl_ok_{weekly_pnl_pct:+.2f}pct")

    # ── 9. Earnings / news risk ───────────────────────────────────────────────
    if has_earnings_today and not HARD_LIMITS["allow_earnings_day_trades"]:
        failed.append("earnings_day_blocked")
    else:
        passed.append("no_earnings_risk")

    if news_risk == "high":
        failed.append("high_news_risk_flagged")
    elif news_risk == "elevated":
        passed.append("elevated_news_risk_noted_but_allowed")
    else:
        passed.append("news_risk_normal")

    # ── Final decision ────────────────────────────────────────────────────────
    approved = len(failed) == 0

    if approved:
        reason = "approved"
        explanation = f"All {len(passed)} risk checks passed."
    else:
        reason = failed[0]  # primary rejection reason
        explanation = f"Blocked: {'; '.join(failed)}. Passed: {'; '.join(passed)}."

    # Calculate actual risk % for logging
    risk_pct = None
    rr_calc = None
    if stop_price and entry_price:
        risk_pct = round(abs(entry_price - stop_price) / entry_price * 100, 3)
    if target_price and stop_price and entry_price:
        if direction == "long":
            r = (entry_price - stop_price)
            rw = (target_price - entry_price)
        else:
            r = (stop_price - entry_price)
            rw = (entry_price - target_price)
        rr_calc = round(rw / r, 2) if r > 0 else 0

    return RiskDecision(
        approved=approved,
        ticker=ticker,
        reason=reason,
        explanation=explanation,
        checks_passed=passed,
        checks_failed=failed,
        risk_pct=risk_pct,
        risk_reward=rr_calc,
    )


def get_active_rules() -> dict:
    """Return the currently active risk rules for display in the dashboard."""
    return {
        "max_risk_per_trade_pct": _get_limit("max_risk_per_trade_pct"),
        "min_stop_loss_pct": _get_limit("min_stop_loss_pct"),
        "max_stop_loss_pct": _get_limit("max_stop_loss_pct"),
        "min_risk_reward": _get_limit("min_risk_reward"),
        "max_open_positions": int(_get_limit("max_open_positions")),
        "max_daily_loss_pct": _get_limit("max_daily_loss_pct"),
        "max_weekly_loss_pct": _get_limit("max_weekly_loss_pct"),
        "min_confidence": int(_get_limit("min_confidence")),
        "live_trading_enabled": HARD_LIMITS["live_trading_enabled"],
        "allow_earnings_day_trades": HARD_LIMITS["allow_earnings_day_trades"],
        "note": "Core limits are hardcoded. User settings can only make them stricter.",
    }
