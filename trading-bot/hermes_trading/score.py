"""Score a list of trades against goal.yaml. Returns float in [-1, +1]."""
from __future__ import annotations
import math
from typing import Any


def score(trades: list[dict[str, Any]], goal: dict[str, Any]) -> float:
    if not trades:
        return 0.0

    returns = [t["pnl_pct"] for t in trades if "pnl_pct" in t]
    if not returns:
        return 0.0

    # Realised return component
    total_return = sum(returns)
    target = goal.get("target_return_30d", 0.05)
    return_score = min(total_return / target, 1.0) if target else 0.0

    # Drawdown component
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in returns:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    max_allowed_dd = goal.get("max_drawdown", 0.08)
    dd_score = 1.0 - min(max_dd / max_allowed_dd, 1.0) if max_allowed_dd else 0.0

    # Sharpe component
    if len(returns) > 1:
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_r = math.sqrt(variance) if variance > 0 else 1e-9
        sharpe = mean_r / std_r * math.sqrt(len(returns))
    else:
        sharpe = 0.0

    min_sharpe = goal.get("min_sharpe", 1.0)
    sharpe_score = min(sharpe / min_sharpe, 1.0) if min_sharpe else 0.0

    composite = (return_score * 0.5) + (dd_score * 0.3) + (sharpe_score * 0.2)

    # Apply floor for badly negative outcomes
    failure_below = goal.get("failure_below", -0.04)
    if total_return < failure_below:
        composite = max(composite - 0.5, -1.0)

    return max(-1.0, min(1.0, composite))
