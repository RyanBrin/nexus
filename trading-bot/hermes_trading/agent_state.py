"""Agent State — Hermes status, mode, and configurable settings.

Separates what the user can change (settings) from what they cannot (risk limits).
Settings are persisted to state/hermes_settings.json.
Status is updated by the trading loops at runtime.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
SETTINGS_FILE = STATE / "hermes_settings.json"
STATUS_FILE   = STATE / "agent_status.json"

# ── Modes ─────────────────────────────────────────────────────────────────────
MODE_DISABLED        = "disabled"
MODE_PAPER           = "paper_trading"
MODE_MANUAL_APPROVAL = "manual_approval"
MODE_LIVE            = "live_disabled"     # always "disabled" for now

# ── Default settings (user-configurable) ──────────────────────────────────────
DEFAULT_SETTINGS = {
    "mode": MODE_PAPER,
    "btc_enabled": True,
    "stocks_enabled": True,
    "learning_mode": True,
    "news_filter_enabled": True,
    "elliott_wave_enabled": True,
    "scan_interval_seconds": 300,
    "min_confidence": 65,
    "min_risk_reward": 1.5,
    "max_paper_trades_per_day": 5,
    "max_paper_loss_per_day_pct": 3.0,
    "max_paper_loss_per_week_pct": 6.0,
    "max_open_paper_trades": 3,
    "risk": {
        "max_risk_per_trade_pct": 1.5,
        "min_stop_loss_pct": 0.5,
        "max_stop_loss_pct": 3.0,
        "min_risk_reward": 1.5,
        "max_open_positions": 3,
        "max_daily_loss_pct": 3.0,
        "max_weekly_loss_pct": 6.0,
        "min_confidence": 65,
    },
    "market_condition": "unknown",
    "last_updated": "",
}


def load_settings() -> dict:
    # Try Supabase first
    try:
        import asyncio
        from hermes_trading.db import load_settings_db
        db_settings = asyncio.run(load_settings_db())
        if db_settings:
            return {**DEFAULT_SETTINGS, **db_settings}
    except Exception:
        pass
    # Local file fallback
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text())}
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    settings["last_updated"] = datetime.now(timezone.utc).isoformat()
    # Write local file
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2))
    # Persist to Supabase
    try:
        import asyncio
        from hermes_trading.db import save_settings_db
        asyncio.run(save_settings_db(settings))
    except Exception:
        pass


def update_setting(key: str, value) -> None:
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def get_mode() -> str:
    return load_settings().get("mode", MODE_PAPER)


# ── Runtime status (written by trading loops) ──────────────────────────────────

def load_status() -> dict:
    if not STATUS_FILE.exists():
        return _default_status()
    try:
        return json.loads(STATUS_FILE.read_text())
    except Exception:
        return _default_status()


def _default_status() -> dict:
    return {
        "running": False,
        "mode": MODE_PAPER,
        "btc_loop_running": False,
        "stock_loop_running": False,
        "last_btc_tick": None,
        "last_stock_scan": None,
        "next_stock_scan": None,
        "active_strategy": None,
        "active_risk_profile": "default",
        "market_condition": "unknown",
        "open_paper_trades": [],
        "tickers_being_scanned": [],
        "last_strategy_review": None,
        "trades_since_last_review": 0,
        "errors": [],
        "uptime_start": None,
    }


def write_status(updates: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    current = load_status()
    current.update(updates)
    current["last_updated"] = datetime.now(timezone.utc).isoformat()
    STATUS_FILE.write_text(json.dumps(current, indent=2))


def mark_running(mode: str = MODE_PAPER) -> None:
    write_status({
        "running": True,
        "mode": mode,
        "uptime_start": datetime.now(timezone.utc).isoformat(),
    })


def mark_btc_tick(price: float, open_trade: Optional[dict] = None) -> None:
    updates = {
        "btc_loop_running": True,
        "last_btc_tick": datetime.now(timezone.utc).isoformat(),
    }
    if open_trade:
        updates["open_btc_trade"] = open_trade
    write_status(updates)


def mark_stock_scan(tickers: list[str]) -> None:
    import datetime as dt
    nxt = (datetime.now(timezone.utc).timestamp() + 300)
    write_status({
        "stock_loop_running": True,
        "last_stock_scan": datetime.now(timezone.utc).isoformat(),
        "next_stock_scan": datetime.fromtimestamp(nxt, tz=timezone.utc).isoformat(),
        "tickers_being_scanned": tickers,
    })


def log_error(error: str) -> None:
    status = load_status()
    errors = status.get("errors", [])
    errors.append({"ts": datetime.now(timezone.utc).isoformat(), "error": error})
    errors = errors[-20:]  # keep last 20
    write_status({"errors": errors})
