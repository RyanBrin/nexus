"""Phase tracker — checks pass conditions and reports progress toward each phase goal.

ChatGPT's recommended framework:
  Phase 1: 100 paper trades, positive expectancy, PF > 1.3, max DD < 10%
  Phase 2: Manual approval trades
  Phase 3: Live tiny with kill switch
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

import yaml

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))


def _load_goal() -> dict:
    with open(STATE / "goal.yaml") as f:
        return yaml.safe_load(f) or {}


def check_phase_progress(perf_dict: dict, trades: list[dict]) -> dict:
    """Check how close we are to passing the current phase.
    Returns a structured progress report.
    """
    goal = _load_goal()
    current_phase = goal.get("current_phase", 1)
    phases = goal.get("phases", {})
    phase_def = phases.get(current_phase, {})
    conditions = phase_def.get("pass_conditions", {})

    n = perf_dict.get("total_trades", 0)
    min_trades = phase_def.get("min_trades", 100)
    expectancy = perf_dict.get("expectancy_pct", 0)
    profit_factor = perf_dict.get("profit_factor", 0)
    max_dd = perf_dict.get("max_drawdown_pct", 0)
    has_edge = perf_dict.get("has_edge", False)

    # Check each condition
    checks = {}

    if "min_trades" in phase_def:
        checks["trades_progress"] = {
            "label": f"Minimum trades ({n}/{min_trades})",
            "passed": n >= min_trades,
            "value": n,
            "target": min_trades,
            "progress_pct": min(100, round(n / min_trades * 100)),
        }

    if conditions.get("expectancy_positive"):
        checks["expectancy"] = {
            "label": "Positive expectancy",
            "passed": expectancy > 0,
            "value": f"{expectancy:+.4f}%",
            "target": "> 0%",
            "note": "Requires 25+ trades to be meaningful" if n < 25 else "",
        }

    if "min_profit_factor" in conditions:
        target_pf = conditions["min_profit_factor"]
        checks["profit_factor"] = {
            "label": f"Profit factor (target > {target_pf})",
            "passed": profit_factor >= target_pf,
            "value": round(profit_factor, 2),
            "target": f"> {target_pf}",
        }

    if "max_drawdown_pct" in conditions:
        target_dd = conditions["max_drawdown_pct"]
        checks["max_drawdown"] = {
            "label": f"Max drawdown (limit < {target_dd}%)",
            "passed": max_dd < target_dd,
            "value": f"{max_dd:.2f}%",
            "target": f"< {target_dd}%",
        }

    if conditions.get("every_trade_has_stop"):
        trades_with_stop = sum(1 for t in trades if t.get("stop_loss_price") or t.get("stop_loss_pct"))
        total = len(trades)
        checks["stop_loss_logged"] = {
            "label": "Every trade has stop loss",
            "passed": total == 0 or trades_with_stop == total,
            "value": f"{trades_with_stop}/{total}",
            "target": "100%",
        }

    if conditions.get("every_trade_has_reason"):
        trades_with_reason = sum(1 for t in trades if t.get("reasons") or t.get("entry_reason"))
        total = len(trades)
        checks["reason_logged"] = {
            "label": "Every trade has logged reason",
            "passed": total == 0 or trades_with_reason == total,
            "value": f"{trades_with_reason}/{total}",
            "target": "100%",
        }

    passed_count = sum(1 for c in checks.values() if c.get("passed"))
    total_checks = len(checks)
    phase_passed = total_checks > 0 and passed_count == total_checks

    return {
        "current_phase": current_phase,
        "phase_name": phase_def.get("name", f"Phase {current_phase}"),
        "phase_description": phase_def.get("description", ""),
        "unlock_next": phase_def.get("unlock_next", ""),
        "checks": checks,
        "passed_count": passed_count,
        "total_checks": total_checks,
        "phase_passed": phase_passed,
        "overall_progress_pct": round(passed_count / total_checks * 100) if total_checks else 0,
        "data_quality": perf_dict.get("data_quality", "insufficient"),
        "verdict": _phase_verdict(phase_passed, passed_count, total_checks, n, min_trades, expectancy),
    }


def _phase_verdict(passed: bool, passed_count: int, total: int, n: int, min_trades: int, expectancy: float) -> str:
    if passed:
        return f"✓ Phase complete! All {total} conditions met. Ready to advance."
    if n < 25:
        return f"Collecting data — {n}/{min_trades} trades. Need at least 25 for meaningful stats."
    if n < min_trades:
        return f"Progress: {passed_count}/{total} conditions met. Need {min_trades - n} more trades."
    if expectancy <= 0:
        return "No edge detected yet. Strategy needs improvement before advancing."
    return f"Close — {passed_count}/{total} conditions met. See failed checks above."
