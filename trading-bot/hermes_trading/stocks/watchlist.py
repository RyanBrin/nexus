"""Stock watchlist — manual ticker management with per-stock trading toggle."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import json
import os
from pathlib import Path

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent.parent / "state"))
WATCHLIST_FILE = STATE / "stock_watchlist.json"

# Valid position states
POSITION_WATCHING   = "watching"
POSITION_NO_POS     = "no_position"
POSITION_IN_TRADE   = "in_trade"
POSITION_EXITED     = "exited"

# Valid signal states
SIGNAL_NO_SETUP      = "no_valid_setup"
SIGNAL_TREND_UNCLEAR = "trend_unclear"
SIGNAL_WAITING_RETRACE = "waiting_for_retracement"
SIGNAL_WAVE_2        = "watching_possible_wave_2"
SIGNAL_WAVE_4        = "watching_possible_wave_4"
SIGNAL_INVALIDATED   = "invalidated_setup"
SIGNAL_ENTRY         = "entry_confirmed"
SIGNAL_EXIT          = "exit_signal_triggered"
SIGNAL_WATCHING      = "watching"


@dataclass
class StockEntry:
    ticker: str
    company_name: str = ""
    trading_enabled: bool = False          # master on/off switch
    current_price: Optional[float] = None
    daily_change_pct: Optional[float] = None
    position_status: str = POSITION_WATCHING
    entry_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    risk_pct: float = 1.5                  # default 1.5% stop
    confidence_score: int = 0              # 0-100
    signal: str = SIGNAL_NO_SETUP
    hermes_notes: str = ""
    last_updated: str = ""
    # Elliott Wave fields
    wave_count: str = ""
    fib_zone: str = ""
    trend: str = ""
    risk_reward: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "StockEntry":
        # Only pass known fields to avoid future schema issues
        known = {k: v for k, v in d.items() if k in StockEntry.__dataclass_fields__}
        return StockEntry(**known)


DEFAULT_WATCHLIST: list[StockEntry] = [
    StockEntry(ticker="AAPL",  company_name="Apple Inc.",           trading_enabled=False),
    StockEntry(ticker="NVDA",  company_name="NVIDIA Corporation",   trading_enabled=False),
    StockEntry(ticker="TSLA",  company_name="Tesla, Inc.",          trading_enabled=False),
    StockEntry(ticker="AMD",   company_name="Advanced Micro Devices", trading_enabled=False),
    StockEntry(ticker="MSFT",  company_name="Microsoft Corporation", trading_enabled=False),
]


def load_watchlist() -> list[StockEntry]:
    if not WATCHLIST_FILE.exists():
        save_watchlist(DEFAULT_WATCHLIST)
        return list(DEFAULT_WATCHLIST)
    try:
        data = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        return [StockEntry.from_dict(d) for d in data]
    except Exception:
        return list(DEFAULT_WATCHLIST)


def save_watchlist(stocks: list[StockEntry]) -> None:
    WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_FILE.write_text(
        json.dumps([s.to_dict() for s in stocks], indent=2),
        encoding="utf-8"
    )


def get_stock(ticker: str) -> Optional[StockEntry]:
    return next((s for s in load_watchlist() if s.ticker == ticker.upper()), None)


def upsert_stock(stock: StockEntry) -> None:
    stocks = load_watchlist()
    for i, s in enumerate(stocks):
        if s.ticker == stock.ticker.upper():
            stocks[i] = stock
            save_watchlist(stocks)
            return
    stocks.append(stock)
    save_watchlist(stocks)


def remove_stock(ticker: str) -> bool:
    stocks = load_watchlist()
    new = [s for s in stocks if s.ticker != ticker.upper()]
    if len(new) == len(stocks):
        return False
    save_watchlist(new)
    return True


def toggle_trading(ticker: str, enabled: bool) -> bool:
    stock = get_stock(ticker)
    if not stock:
        return False
    stock.trading_enabled = enabled
    upsert_stock(stock)
    return True


def update_price(ticker: str, price: float, change_pct: float) -> None:
    stock = get_stock(ticker)
    if not stock:
        return
    stock.current_price = price
    stock.daily_change_pct = change_pct
    stock.last_updated = datetime.now(timezone.utc).isoformat()
    upsert_stock(stock)
