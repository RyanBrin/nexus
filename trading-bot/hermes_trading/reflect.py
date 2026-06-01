"""
Reflection engine -- batch-based, strategy-registry-aware.

Key rules (per ChatGPT advice):
  - Reflect only after BATCH_SIZE trades (default 25), not every 5
  - Locked strategies are NEVER modified
  - Every reflection creates a NEW named strategy version (clone + modify)
  - Full reason report logged for every reflection
  - Two modes: --fallback (deterministic) and --hermes (Claude AI)
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

STATE = Path(os.getenv("STATE_DIR", str(Path(__file__).parent.parent / "state")))

# Only reflect after this many trades — prevents overreacting to noise
BATCH_SIZE = int(os.getenv("REFLECT_BATCH_SIZE", "25"))


def _load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _bump_version(current):
    try:
        n = int(current)
    except (ValueError, TypeError):
        n = 1
    return str(n + 1).zfill(2)


def _append_hypothesis(h):
    with open(STATE / "hypotheses.jsonl", "a") as f:
        f.write(json.dumps({**h, "ts": datetime.now(timezone.utc).isoformat()}) + "\n")


def _load_all_trades():
    """Load trades from Supabase if available, else local file."""
    try:
        import asyncio
        from hermes_trading import db
        return asyncio.run(db.load_trades(500))
    except Exception:
        pass
    path = STATE / "trades.jsonl"
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


def _trades_since_last_reflect(all_trades: list[dict]) -> list[dict]:
    """Return trades since the last reflection event."""
    hyp_file = STATE / "hypotheses.jsonl"
    if not hyp_file.exists():
        return all_trades
    lines = [l for l in hyp_file.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
    if not lines:
        return all_trades
    try:
        last = json.loads(lines[-1])
        last_ts = last.get("ts", "")
        return [t for t in all_trades if (t.get("exit_ts") or "") > last_ts]
    except Exception:
        return all_trades


def _should_reflect(trades_since_last: list[dict]) -> bool:
    return len(trades_since_last) >= BATCH_SIZE


def _build_performance_summary(trades: list[dict], strategy_name: str) -> str:
    from hermes_trading import performance
    perf = performance.calculate(strategy_name, trades)
    d = perf.to_dict()
    return (
        f"Trades: {d['total_trades']} | Win rate: {d['win_rate_pct']}% | "
        f"Avg win: +{d['avg_win_pct']:.3f}% | Avg loss: -{d['avg_loss_pct']:.3f}% | "
        f"Profit factor: {d['profit_factor']} | Expectancy: {d['expectancy_pct']:.4f}%/trade | "
        f"Max DD: {d['max_drawdown_pct']:.2f}% | Data quality: {d['data_quality']}\n"
        f"Verdict: {perf.verdict()}"
    )


# ── Reflect modes ─────────────────────────────────────────────────────────────

def reflect_fallback(force: bool = False):
    from hermes_trading import strategy_registry

    strategy_registry.bootstrap_from_existing()
    active_name = strategy_registry.get_active_strategy_name()

    if strategy_registry.is_locked(active_name) and not force:
        print(f"Strategy '{active_name}' is LOCKED — skipping reflection.")
        return

    all_trades = _load_all_trades()
    new_trades = _trades_since_last_reflect(all_trades)

    if not force and not _should_reflect(new_trades):
        print(f"Only {len(new_trades)} trades since last reflection (need {BATCH_SIZE}). Skipping.")
        return

    goal = _load_yaml(STATE / "goal.yaml")
    strategy = strategy_registry.load_strategy_params(active_name) or _load_yaml(STATE / "strategy.yaml")

    from hermes_trading.score import score as compute_score
    from hermes_trading import performance

    s = compute_score(new_trades, goal)
    perf = performance.calculate(active_name, all_trades)
    perf_dict = perf.to_dict()

    target = goal.get("target_return_30d", 0.05)
    max_dd = goal.get("max_drawdown", 0.08)
    total_return = sum(t.get("pnl_pct", 0) for t in new_trades)

    # Determine what to change
    if total_return < target:
        old = strategy["entry"]["threshold"]
        new_val = old + 2
        strategy["entry"]["threshold"] = new_val
        changed = "entry.threshold"
        rationale = (f"Batch return {total_return*100:.2f}% < target {target*100:.0f}%; "
                     f"loosened RSI threshold {old} → {new_val}")
    else:
        cumulative = peak = worst_dd = 0.0
        for t in new_trades:
            cumulative += t.get("pnl_pct", 0)
            peak = max(peak, cumulative)
            worst_dd = max(worst_dd, peak - cumulative)
        if worst_dd > max_dd:
            old = strategy["stop_loss_pct"]
            new_val = round(old - 0.2, 2)
            strategy["stop_loss_pct"] = new_val
            changed = "stop_loss_pct"
            rationale = (f"Batch drawdown {worst_dd*100:.2f}% > max {max_dd*100:.0f}%; "
                         f"tightened stop_loss {old} → {new_val}")
        else:
            print(f"Batch score acceptable ({s:.3f}) — no change needed.")
            _append_hypothesis({
                "mode": "fallback", "changed": "none",
                "rationale": f"Score {s:.3f} acceptable over {len(new_trades)} trades. No change.",
                "score_before": s, "version": active_name,
                "batch_size": len(new_trades), "performance": perf_dict
            })
            return

    # Create new strategy version
    old_version = strategy.get("version", "01")
    new_version_num = _bump_version(old_version)
    new_name = f"v{new_version_num}"
    strategy["version"] = new_version_num

    strategy_registry.clone_strategy(active_name, new_name, reason=rationale)
    strategy_registry.save_strategy_params(new_name, strategy)
    strategy_registry.set_active_strategy(new_name)
    strategy_registry.update_performance(active_name, perf_dict)

    _append_hypothesis({
        "mode": "fallback",
        "changed": changed,
        "rationale": rationale,
        "score_before": s,
        "version": new_name,
        "previous_version": active_name,
        "batch_size": len(new_trades),
        "performance": perf_dict,
        "verdict": perf.verdict(),
    })
    print(f"Reflected (fallback): {rationale}")
    print(f"  New strategy: {new_name} | Expectancy: {perf_dict['expectancy_pct']:.4f}%/trade")


def reflect_hermes(force: bool = False):
    import anthropic
    from hermes_trading import strategy_registry

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY not set; using fallback", file=sys.stderr)
        reflect_fallback(force=force)
        return

    strategy_registry.bootstrap_from_existing()
    active_name = strategy_registry.get_active_strategy_name()

    if strategy_registry.is_locked(active_name) and not force:
        print(f"Strategy '{active_name}' is LOCKED — skipping reflection.")
        return

    all_trades = _load_all_trades()
    new_trades = _trades_since_last_reflect(all_trades)

    if not force and not _should_reflect(new_trades):
        print(f"Only {len(new_trades)} trades since last reflection (need {BATCH_SIZE}). Skipping.")
        return

    goal = _load_yaml(STATE / "goal.yaml")
    strategy = strategy_registry.load_strategy_params(active_name) or _load_yaml(STATE / "strategy.yaml")

    from hermes_trading.score import score as compute_score
    from hermes_trading import performance

    current_score = compute_score(new_trades, goal)
    perf = performance.calculate(active_name, all_trades)
    perf_dict = perf.to_dict()
    perf_summary = _build_performance_summary(all_trades, active_name)

    from hermes_trading import performance as perf_module
    from hermes_trading.phase_tracker import check_phase_progress

    all_perf = perf_module.calculate(active_name, all_trades)
    phase_progress = check_phase_progress(all_perf.to_dict(), all_trades)

    prompt = (
        "You are Hermes, a disciplined trading strategy optimizer.\n\n"
        "YOUR OBJECTIVE: Maximize risk-adjusted expectancy while staying inside strict "
        "drawdown limits. Do NOT optimize for raw profit — that leads to reckless behavior.\n\n"
        f"MASTER GOAL: {goal.get('reflection_objective', 'maximize_risk_adjusted_expectancy')}\n\n"
        f"CURRENT PHASE: {phase_progress['phase_name']}\n"
        f"PHASE GOAL: {phase_progress['phase_description']}\n"
        f"PHASE PROGRESS: {phase_progress['passed_count']}/{phase_progress['total_checks']} conditions met\n"
        f"PHASE VERDICT: {phase_progress['verdict']}\n\n"
        f"PERFORMANCE SUMMARY ({len(new_trades)} trades since last reflection):\n{perf_summary}\n\n"
        f"GOAL CONSTRAINTS:\n"
        f"  max_drawdown: {goal.get('max_drawdown', 0.08)*100:.0f}%\n"
        f"  max_risk_per_trade: {goal.get('max_risk_per_trade', 0.015)*100:.1f}%\n"
        f"  min_profit_factor: 1.3\n"
        f"  target_expectancy: > 0\n\n"
        f"CURRENT STRATEGY ({active_name}):\n{yaml.dump(strategy)}\n"
        f"RECENT TRADES (last {min(25, len(new_trades))}):\n"
        f"{json.dumps(new_trades[-25:], indent=2)}\n"
        f"CURRENT SCORE: {current_score:.3f} (range -1 to +1)\n\n"
        "Rules:\n"
        "- Change exactly ONE variable. Scientific method.\n"
        "- NEVER increase risk beyond the goal constraints.\n"
        "- NEVER remove stop_loss or set it to 0.\n"
        "- If expectancy is positive and drawdown is under limit: make a SMALL conservative change.\n"
        "- If expectancy is negative: diagnose why (bad entries? too early? wrong threshold?) and change the most likely cause.\n"
        "- If phase conditions are not met: focus on the failing condition.\n"
        "- Output ONLY valid YAML for the updated strategy. Nothing else.\n"
        "- Do not change the version field.\n"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.splitlines()[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.splitlines()[:-1])

        updated = yaml.safe_load(raw)
        if not isinstance(updated, dict):
            reflect_fallback(force=force)
            return

        old_version = strategy.get("version", "01")
        new_version_num = _bump_version(old_version)
        new_name = f"v{new_version_num}"
        updated["version"] = new_version_num

        strategy_registry.clone_strategy(active_name, new_name,
                                          reason=f"Claude reflection from {active_name}")
        strategy_registry.save_strategy_params(new_name, updated)
        strategy_registry.set_active_strategy(new_name)
        strategy_registry.update_performance(active_name, perf_dict)

        _append_hypothesis({
            "mode": "hermes",
            "score_before": current_score,
            "version": new_name,
            "previous_version": active_name,
            "batch_size": len(new_trades),
            "performance": perf_dict,
            "verdict": perf.verdict(),
            "raw_output": raw[:400],
        })
        print(f"Reflected (hermes/claude): {active_name} → {new_name}")
        print(f"  Expectancy: {perf_dict['expectancy_pct']:.4f}%/trade | "
              f"Data quality: {perf_dict['data_quality']}")

    except Exception as exc:
        print(f"Anthropic API error: {exc}; using fallback", file=sys.stderr)
        reflect_fallback(force=force)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fallback", action="store_true")
    group.add_argument("--hermes", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Bypass batch size check and locked strategy guard")
    args = parser.parse_args()
    if args.fallback:
        reflect_fallback(force=args.force)
    else:
        reflect_hermes(force=args.force)


if __name__ == "__main__":
    main()
