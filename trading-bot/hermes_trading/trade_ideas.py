"""Trade Ideas log — every setup Hermes considered, whether approved or rejected.

This is the core visibility layer. Every idea, every rejection, every approval
is logged here so the user can see exactly what Hermes is thinking.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
IDEAS_FILE = STATE / "trade_ideas.jsonl"

STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_WATCHING = "watching"


@dataclass
class TradeIdea:
    ticker: str
    asset_type: str              # "stock" or "btc"
    direction: str               # "long" or "short"
    entry_price: Optional[float]
    stop_price: Optional[float]
    target_price: Optional[float]
    risk_pct: Optional[float]
    risk_reward: Optional[float]
    confidence: int              # 0-100
    strategy_version: str
    # Analysis
    chart_reason: str            # why the chart looks good
    wave_count: str
    fib_zone: str
    trend: str
    # News
    news_summary: str
    news_risk: str               # "normal" / "elevated" / "high"
    # Decision
    status: str                  # "approved" / "rejected" / "watching"
    rejection_reason: str        # empty if approved
    risk_checks_passed: list
    risk_checks_failed: list
    # Memory / learning context
    similar_past_setups: str
    hermes_notes: str
    # Timestamps
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now

    def to_dict(self) -> dict:
        return asdict(self)


def append_idea(idea: TradeIdea) -> None:
    IDEAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(IDEAS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(idea.to_dict()) + "\n")


def load_ideas(limit: int = 100, status: Optional[str] = None) -> list[dict]:
    if not IDEAS_FILE.exists():
        return []
    try:
        lines = [l for l in IDEAS_FILE.read_text(encoding="utf-8-sig").strip().splitlines() if l.strip()]
        ideas = [json.loads(l) for l in lines]
        if status:
            ideas = [i for i in ideas if i.get("status") == status]
        return ideas[-limit:]
    except Exception:
        return []


def load_rejected(limit: int = 50) -> list[dict]:
    return load_ideas(limit=limit, status=STATUS_REJECTED)


def load_approved(limit: int = 50) -> list[dict]:
    return load_ideas(limit=limit, status=STATUS_APPROVED)


def get_stats() -> dict:
    all_ideas = load_ideas(limit=10000)
    approved = [i for i in all_ideas if i.get("status") == STATUS_APPROVED]
    rejected = [i for i in all_ideas if i.get("status") == STATUS_REJECTED]
    watching = [i for i in all_ideas if i.get("status") == STATUS_WATCHING]

    # Rejection reason breakdown
    reasons: dict[str, int] = {}
    for i in rejected:
        r = i.get("rejection_reason", "unknown")
        reasons[r] = reasons.get(r, 0) + 1

    return {
        "total_ideas": len(all_ideas),
        "approved": len(approved),
        "rejected": len(rejected),
        "watching": len(watching),
        "approval_rate_pct": round(len(approved) / len(all_ideas) * 100, 1) if all_ideas else 0,
        "top_rejection_reasons": sorted(reasons.items(), key=lambda x: -x[1])[:5],
    }
