"""Per-strategy performance calculator.

Computes the stats ChatGPT recommended:
  - win rate
  - average win / average loss
  - profit factor
  - expectancy (the key metric)
  - max drawdown
  - total trades / wins / losses
  - consecutive win/loss streaks
  - market condition breakdown (if available)

Expectancy = (win_rate × avg_win) - (loss_rate × avg_loss)
A positive expectancy means the strategy has edge.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyPerformance:
    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float            # 0-1
    avg_win_pct: float         # average winning trade %
    avg_loss_pct: float        # average losing trade % (positive number)
    profit_factor: float       # gross wins / gross losses (> 1 = profitable)
    expectancy_pct: float      # expected % gain per trade
    max_drawdown_pct: float    # peak-to-trough %
    total_return_pct: float    # sum of all pnl
    best_trade_pct: float
    worst_trade_pct: float
    avg_win_loss_ratio: float  # avg win / avg loss (risk/reward achieved)
    longest_win_streak: int
    longest_loss_streak: int
    data_quality: str          # "insufficient" / "early_signal" / "useful" / "reliable"

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate_pct": round(self.win_rate * 100, 1),
            "avg_win_pct": round(self.avg_win_pct * 100, 3),
            "avg_loss_pct": round(self.avg_loss_pct * 100, 3),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy_pct": round(self.expectancy_pct * 100, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct * 100, 2),
            "total_return_pct": round(self.total_return_pct * 100, 2),
            "best_trade_pct": round(self.best_trade_pct * 100, 3),
            "worst_trade_pct": round(self.worst_trade_pct * 100, 3),
            "avg_win_loss_ratio": round(self.avg_win_loss_ratio, 2),
            "longest_win_streak": self.longest_win_streak,
            "longest_loss_streak": self.longest_loss_streak,
            "data_quality": self.data_quality,
            "has_edge": self.expectancy_pct > 0 and self.total_trades >= 25,
        }

    def verdict(self) -> str:
        if self.total_trades < 10:
            return "Too few trades to evaluate."
        if self.total_trades < 25:
            return f"Early data ({self.total_trades} trades). Need 25+ for a signal."
        if self.expectancy_pct <= 0:
            return f"No edge detected. Expectancy is {self.expectancy_pct*100:.3f}% per trade."
        if self.total_trades < 100:
            return (f"Early positive signal. Expectancy: {self.expectancy_pct*100:.3f}%/trade, "
                    f"Win rate: {self.win_rate*100:.0f}%, PF: {self.profit_factor:.2f}. "
                    f"Need 100+ trades to confirm.")
        return (f"Useful data. Expectancy: {self.expectancy_pct*100:.3f}%/trade, "
                f"Win rate: {self.win_rate*100:.0f}%, PF: {self.profit_factor:.2f}, "
                f"Max DD: {self.max_drawdown_pct*100:.1f}%.")


def _data_quality(n: int) -> str:
    if n < 25:
        return "insufficient"
    if n < 50:
        return "early_signal"
    if n < 100:
        return "useful"
    return "reliable"


def _streaks(results: list[bool]) -> tuple[int, int]:
    """Return (longest_win_streak, longest_loss_streak)."""
    max_win = max_loss = cur_win = cur_loss = 0
    for r in results:
        if r:
            cur_win += 1; cur_loss = 0
        else:
            cur_loss += 1; cur_win = 0
        max_win = max(max_win, cur_win)
        max_loss = max(max_loss, cur_loss)
    return max_win, max_loss


def _max_drawdown(pnl_series: list[float]) -> float:
    """Calculate peak-to-trough drawdown from a series of PnL values."""
    peak = 0.0
    max_dd = 0.0
    cumulative = 0.0
    for pnl in pnl_series:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return max_dd


def calculate(strategy_name: str, trades: list[dict]) -> StrategyPerformance:
    """Calculate full performance stats for trades belonging to a strategy."""
    # Filter to this strategy's trades
    strat_trades = [
        t for t in trades
        if t.get("strategy_version") == strategy_name
        or t.get("strategy_name") == strategy_name
    ]

    n = len(strat_trades)

    if n == 0:
        return StrategyPerformance(
            strategy_name=strategy_name, total_trades=0, wins=0, losses=0,
            win_rate=0, avg_win_pct=0, avg_loss_pct=0, profit_factor=0,
            expectancy_pct=0, max_drawdown_pct=0, total_return_pct=0,
            best_trade_pct=0, worst_trade_pct=0, avg_win_loss_ratio=0,
            longest_win_streak=0, longest_loss_streak=0,
            data_quality="insufficient"
        )

    pnl_list = [t.get("pnl_pct", 0) for t in strat_trades]
    win_pnls  = [p for p in pnl_list if p > 0]
    loss_pnls = [p for p in pnl_list if p <= 0]

    wins = len(win_pnls)
    losses = len(loss_pnls)
    win_rate = wins / n if n else 0
    loss_rate = losses / n if n else 0

    avg_win  = sum(win_pnls)  / len(win_pnls)  if win_pnls  else 0.0
    avg_loss = abs(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0.0

    gross_wins   = sum(win_pnls)
    gross_losses = abs(sum(loss_pnls))

    profit_factor = gross_wins / gross_losses if gross_losses > 0 else (float("inf") if gross_wins > 0 else 0.0)
    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    max_dd = _max_drawdown(pnl_list)
    total_return = sum(pnl_list)
    best = max(pnl_list)
    worst = min(pnl_list)
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

    win_streak, loss_streak = _streaks([p > 0 for p in pnl_list])

    return StrategyPerformance(
        strategy_name=strategy_name,
        total_trades=n,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
        profit_factor=profit_factor,
        expectancy_pct=expectancy,
        max_drawdown_pct=max_dd,
        total_return_pct=total_return,
        best_trade_pct=best,
        worst_trade_pct=worst,
        avg_win_loss_ratio=rr_ratio,
        longest_win_streak=win_streak,
        longest_loss_streak=loss_streak,
        data_quality=_data_quality(n),
    )


def calculate_all(trades: list[dict]) -> dict[str, dict]:
    """Calculate performance for every strategy version seen in trades."""
    versions = set(
        t.get("strategy_version") or t.get("strategy_name", "unknown")
        for t in trades
    )
    return {
        v: calculate(v, trades).to_dict()
        for v in sorted(versions)
        if v
    }
