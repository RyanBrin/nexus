"""
Reflection engine -- two modes:
  --fallback   deterministic rules, no AI needed
  --hermes     calls Anthropic API (claude-sonnet-4-6) for AI-driven reflection
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


def _archive(strategy):
    version = strategy.get("version", "00")
    _save_yaml(STATE / "history" / f"v{version}.yaml", strategy)


def _append_hypothesis(h):
    with open(STATE / "hypotheses.jsonl", "a") as f:
        f.write(json.dumps({**h, "ts": datetime.now(timezone.utc).isoformat()}) + "\n")


def _recent_trades(n=25):
    path = STATE / "trades.jsonl"
    if not path.exists():
        return []
    lines = [l for l in path.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
    return [json.loads(l) for l in lines[-n:]]


def reflect_fallback():
    goal = _load_yaml(STATE / "goal.yaml")
    strategy = _load_yaml(STATE / "strategy.yaml")
    trades = _recent_trades(25)

    from hermes_trading.score import score as compute_score
    s = compute_score(trades, goal)

    target = goal.get("target_return_30d", 0.05)
    max_dd = goal.get("max_drawdown", 0.08)
    total_return = sum(t.get("pnl_pct", 0) for t in trades)

    if total_return < target:
        old = strategy["entry"]["threshold"]
        new = old + 2
        strategy["entry"]["threshold"] = new
        changed = "entry.threshold"
        rationale = f"return {total_return:.3f} < target {target}; loosened RSI threshold {old} -> {new}"
    else:
        cumulative = peak = worst_dd = 0.0
        for t in trades:
            cumulative += t.get("pnl_pct", 0)
            peak = max(peak, cumulative)
            worst_dd = max(worst_dd, peak - cumulative)
        if worst_dd > max_dd:
            old = strategy["stop_loss_pct"]
            new = round(old - 0.2, 2)
            strategy["stop_loss_pct"] = new
            changed = "stop_loss_pct"
            rationale = f"drawdown {worst_dd:.3f} > max {max_dd}; tightened stop_loss {old} -> {new}"
        else:
            print("Score acceptable -- no change this cycle.")
            return

    _archive({**strategy, "version": strategy["version"]})
    strategy["version"] = _bump_version(strategy["version"])
    _save_yaml(STATE / "strategy.yaml", strategy)
    _append_hypothesis({"mode": "fallback", "changed": changed, "rationale": rationale,
                        "score_before": s, "version": strategy["version"]})
    print(f"Reflected (fallback): {rationale}")
    print(f"  strategy.yaml -> v{strategy['version']}")


def reflect_hermes():
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY not set; using fallback", file=sys.stderr)
        reflect_fallback()
        return

    goal = _load_yaml(STATE / "goal.yaml")
    strategy = _load_yaml(STATE / "strategy.yaml")
    trades = _recent_trades(25)

    from hermes_trading.score import score as compute_score
    current_score = compute_score(trades, goal)

    prompt = (
        "You are a trading strategy optimizer. Change exactly ONE variable in the strategy YAML to improve performance.\n\n"
        f"GOAL:\n{yaml.dump(goal)}\n"
        f"STRATEGY (v{strategy.get('version')}):\n{yaml.dump(strategy)}\n"
        f"RECENT TRADES ({len(trades)}):\n{json.dumps(trades, indent=2)}\n"
        f"CURRENT SCORE: {current_score:.3f} (range -1 to +1, higher is better)\n\n"
        "Rules:\n"
        "- Change exactly ONE variable. No more.\n"
        "- Output ONLY valid YAML for the updated strategy file. Nothing else.\n"
        "- Do not change the version field (it will be bumped automatically).\n"
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = "\n".join(raw.splitlines()[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.splitlines()[:-1])

        updated = yaml.safe_load(raw)
        if not isinstance(updated, dict):
            print(f"Claude returned non-dict output; using fallback", file=sys.stderr)
            reflect_fallback()
            return

        _archive(strategy)
        updated["version"] = _bump_version(strategy["version"])
        _save_yaml(STATE / "strategy.yaml", updated)
        _append_hypothesis({
            "mode": "hermes",
            "score_before": current_score,
            "version": updated["version"],
            "raw_output": raw[:300],
        })
        print(f"Reflected (hermes/claude): strategy -> v{updated['version']}")

    except Exception as exc:
        print(f"Anthropic API error: {exc}; using fallback", file=sys.stderr)
        reflect_fallback()


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fallback", action="store_true")
    group.add_argument("--hermes", action="store_true")
    args = parser.parse_args()
    reflect_fallback() if args.fallback else reflect_hermes()


if __name__ == "__main__":
    main()
