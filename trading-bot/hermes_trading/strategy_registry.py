"""Strategy registry — named, versioned, lockable strategies.

Each strategy is a YAML file in state/strategies/.
The active strategy is symlinked/referenced by state/strategy.yaml.

A locked strategy cannot be modified by Claude's reflection engine.
Only batch reviews (every 25 trades) can propose a new version.
"""
from __future__ import annotations
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
STRATEGIES_DIR = STATE / "strategies"
ACTIVE_FILE = STATE / "active_strategy.json"


def _ensure_dirs() -> None:
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Strategy metadata ─────────────────────────────────────────────────────────

def get_active_strategy_name() -> str:
    if ACTIVE_FILE.exists():
        try:
            return json.loads(ACTIVE_FILE.read_text())["name"]
        except Exception:
            pass
    return "v01"


def set_active_strategy(name: str) -> None:
    _ensure_dirs()
    meta = load_strategy_meta(name)
    if not meta:
        raise ValueError(f"Strategy '{name}' not found")
    ACTIVE_FILE.write_text(json.dumps({"name": name, "switched_at": _now()}))
    # Sync to the main strategy.yaml the loop reads
    strategy_file = STRATEGIES_DIR / f"{name}.yaml"
    if strategy_file.exists():
        shutil.copy(strategy_file, STATE / "strategy.yaml")


def load_strategy_meta(name: str) -> Optional[dict]:
    """Load metadata (not the strategy params) for a named strategy."""
    meta_file = STRATEGIES_DIR / f"{name}.meta.json"
    if not meta_file.exists():
        return None
    try:
        return json.loads(meta_file.read_text())
    except Exception:
        return None


def save_strategy_meta(name: str, meta: dict) -> None:
    _ensure_dirs()
    meta_file = STRATEGIES_DIR / f"{name}.meta.json"
    meta_file.write_text(json.dumps(meta, indent=2))


def load_strategy_params(name: str) -> Optional[dict]:
    strat_file = STRATEGIES_DIR / f"{name}.yaml"
    if not strat_file.exists():
        # Fall back to main strategy.yaml
        main = STATE / "strategy.yaml"
        if main.exists():
            with open(main) as f:
                return yaml.safe_load(f) or {}
        return None
    with open(strat_file) as f:
        return yaml.safe_load(f) or {}


def save_strategy_params(name: str, params: dict) -> None:
    _ensure_dirs()
    strat_file = STRATEGIES_DIR / f"{name}.yaml"
    with open(strat_file, "w") as f:
        yaml.dump(params, f, default_flow_style=False, sort_keys=False)
    # If this is the active strategy, sync to strategy.yaml
    if get_active_strategy_name() == name:
        shutil.copy(strat_file, STATE / "strategy.yaml")


def is_locked(name: str) -> bool:
    meta = load_strategy_meta(name)
    return bool(meta and meta.get("locked", False))


def lock_strategy(name: str) -> None:
    meta = load_strategy_meta(name) or {}
    meta["locked"] = True
    meta["locked_at"] = _now()
    save_strategy_meta(name, meta)


def unlock_strategy(name: str) -> None:
    meta = load_strategy_meta(name) or {}
    meta["locked"] = False
    save_strategy_meta(name, meta)


def list_strategies() -> list[dict]:
    _ensure_dirs()
    results = []
    for meta_file in sorted(STRATEGIES_DIR.glob("*.meta.json")):
        name = meta_file.stem.replace(".meta", "")
        meta = json.loads(meta_file.read_text())
        params = load_strategy_params(name) or {}
        results.append({
            "name": name,
            "display_name": meta.get("display_name", name),
            "description": meta.get("description", ""),
            "locked": meta.get("locked", False),
            "created_at": meta.get("created_at", ""),
            "locked_at": meta.get("locked_at"),
            "active": get_active_strategy_name() == name,
            "params": params,
            "performance": meta.get("performance", {}),
            "reason_created": meta.get("reason_created", ""),
        })
    return results


def register_strategy(
    name: str,
    params: dict,
    display_name: str = "",
    description: str = "",
    reason_created: str = "",
    locked: bool = False,
) -> None:
    """Create or overwrite a strategy version."""
    _ensure_dirs()
    meta = load_strategy_meta(name) or {}
    meta.update({
        "name": name,
        "display_name": display_name or name,
        "description": description,
        "reason_created": reason_created,
        "locked": locked,
        "created_at": meta.get("created_at", _now()),
        "updated_at": _now(),
    })
    save_strategy_meta(name, meta)
    save_strategy_params(name, params)


def update_performance(name: str, perf: dict) -> None:
    meta = load_strategy_meta(name) or {}
    meta["performance"] = perf
    meta["performance_updated_at"] = _now()
    save_strategy_meta(name, meta)


def clone_strategy(source_name: str, new_name: str, reason: str = "") -> None:
    """Fork an existing strategy into a new named version."""
    params = load_strategy_params(source_name)
    if not params:
        raise ValueError(f"Source strategy '{source_name}' not found")
    src_meta = load_strategy_meta(source_name) or {}
    register_strategy(
        name=new_name,
        params=params,
        display_name=new_name,
        description=f"Forked from {source_name}",
        reason_created=reason or f"Cloned from {source_name}",
        locked=False,
    )


# ── Bootstrap: migrate existing strategy.yaml ─────────────────────────────────

def bootstrap_from_existing() -> None:
    """On first run, import the current strategy.yaml as 'v01'."""
    if list_strategies():
        return  # already bootstrapped
    main_strat = STATE / "strategy.yaml"
    if not main_strat.exists():
        return
    with open(main_strat) as f:
        params = yaml.safe_load(f) or {}
    version = params.get("version", "01")
    name = f"v{version.zfill(2)}"
    register_strategy(
        name=name,
        params=params,
        display_name=f"Strategy {name}",
        description="Initial strategy imported from strategy.yaml",
        reason_created="Bootstrapped from existing strategy on first run",
        locked=False,
    )
    # Set as active
    ACTIVE_FILE.write_text(json.dumps({"name": name, "switched_at": _now()}))
