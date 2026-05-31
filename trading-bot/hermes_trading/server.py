"""FastAPI server — trading dashboard + API endpoints."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from hermes_trading import db

STATE = Path(os.getenv("STATE_DIR", Path(__file__).parent.parent / "state"))
app = FastAPI(title="Nexus Trading", docs_url=None, redoc_url=None)


def _load_yaml_raw(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except Exception:
        return ""


def _fmt_price(v) -> str:
    return f"${v:,.0f}" if isinstance(v, (int, float)) else "—"


def _fmt_pct(v) -> str:
    return f"{v * 100:+.2f}%" if isinstance(v, (int, float)) else "—"


def _fmt_ts(ts: str) -> str:
    try:
        return ts[:16].replace("T", " ")
    except Exception:
        return "—"


@app.get("/status")
async def status():
    heartbeat = await db.read_heartbeat()
    trades = await db.load_trades()
    hypotheses = await db.load_hypotheses()
    strategy_raw = _load_yaml_raw(STATE / "strategy.yaml")
    return {
        "status": heartbeat.get("status", "unknown"),
        "last_tick": heartbeat.get("last_tick"),
        "consecutive_failures": heartbeat.get("consecutive_failures", 0),
        "trade_count": len(trades),
        "hypothesis_count": len(hypotheses),
        "last_hypothesis": hypotheses[-1] if hypotheses else None,
        "strategy": strategy_raw,
        "open_trade": heartbeat.get("open_trade"),
        "last_price": heartbeat.get("last_price"),
        "last_score": heartbeat.get("last_score"),
    }


@app.get("/trades")
async def trades():
    return await db.load_trades()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    trades = await db.load_trades()
    hypotheses = await db.load_hypotheses()
    heartbeat = await db.read_heartbeat()
    strategy = _load_yaml_raw(STATE / "strategy.yaml")

    price = heartbeat.get("last_price")
    score = heartbeat.get("last_score")
    last_tick = heartbeat.get("last_tick", "")
    open_trade = heartbeat.get("open_trade")
    trade_count = len(trades)

    # Stats
    closed = [t for t in trades if t.get("pnl_pct") is not None]
    wins = [t for t in closed if t.get("pnl_pct", 0) > 0]
    losses = [t for t in closed if t.get("pnl_pct", 0) <= 0]
    win_rate = f"{len(wins)/len(closed)*100:.0f}%" if closed else "—"
    total_pnl = sum(t.get("pnl_pct", 0) for t in closed)
    best = max((t.get("pnl_pct", 0) for t in closed), default=None)
    worst = min((t.get("pnl_pct", 0) for t in closed), default=None)

    version = "—"
    for line in strategy.splitlines():
        if line.startswith("version:"):
            version = line.split(":")[-1].strip().strip('"')

    # Open trade card
    open_trade_html = ""
    if open_trade:
        entry_p = open_trade.get("entry_price", 0)
        cur_p = price if isinstance(price, (int, float)) else entry_p
        live_pnl = (cur_p - entry_p) / entry_p if entry_p else 0
        pnl_color = "#22c55e" if live_pnl >= 0 else "#ef4444"
        open_trade_html = f"""
        <div class="open-trade">
          <div class="ot-label">⚡ OPEN TRADE</div>
          <div class="ot-row">
            <span>BTC/USDT {open_trade.get('direction','').upper()}</span>
            <span>Entry: {_fmt_price(entry_p)}</span>
            <span>Current: {_fmt_price(cur_p)}</span>
            <span style="color:{pnl_color};font-weight:700">Live PnL: {_fmt_pct(live_pnl)}</span>
            <span style="color:#64748b">since {_fmt_ts(open_trade.get('entry_ts',''))}</span>
          </div>
        </div>"""

    # Trade rows
    recent = list(reversed(trades[-25:]))
    rows = ""
    for t in recent:
        pnl = t.get("pnl_pct")
        ep = t.get("exit_price")
        exit_p_str = f"${ep:,.0f}" if isinstance(ep, (int, float)) else "—"
        pnl_str = _fmt_pct(pnl) if pnl is not None else "<span style='color:#f59e0b'>open</span>"
        pnl_color = "#22c55e" if pnl and pnl > 0 else "#ef4444" if pnl and pnl < 0 else "#94a3b8"
        src = t.get("source", "rsi")
        src_badge = f"<span class='badge badge-{'tv' if src == 'tradingview' else 'rsi'}'>{src}</span>"
        rows += f"""<tr>
          <td>{_fmt_ts(t.get('entry_ts',''))}</td>
          <td>{t.get('direction','').upper()}</td>
          <td>{_fmt_price(t.get('entry_price'))}</td>
          <td>{exit_p_str}</td>
          <td style="color:{pnl_color};font-weight:600">{pnl_str}</td>
          <td>{t.get('exit_reason','—')}</td>
          <td>v{t.get('strategy_version','?')}</td>
          <td>{src_badge}</td>
        </tr>"""

    # PnL sparkline data
    pnl_data = [t.get("pnl_pct", 0) * 100 for t in closed[-25:]]
    pnl_json = json.dumps(pnl_data)

    # Last reflection
    last_h = hypotheses[-1] if hypotheses else None
    hyp_html = ""
    if last_h:
        hyp_html = f"""
        <div class="hyp-grid">
          <div><span class="hyp-label">Mode</span><span class="hyp-val">{last_h.get('mode','—')}</span></div>
          <div><span class="hyp-label">Changed</span><span class="hyp-val">{last_h.get('changed','—')}</span></div>
          <div><span class="hyp-label">Score before</span><span class="hyp-val">{last_h.get('score_before','—')}</span></div>
          <div><span class="hyp-label">Strategy</span><span class="hyp-val">v{last_h.get('version','—')}</span></div>
        </div>
        <p style="color:#94a3b8;font-size:0.85rem;margin-top:10px">{last_h.get('rationale','')}</p>"""
    else:
        hyp_html = "<p style='color:#64748b'>No reflections yet — fires after every 5 closed trades.</p>"

    score_color = "#22c55e" if isinstance(score, float) and score > 0 else "#ef4444" if isinstance(score, float) and score < 0 else "#94a3b8"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="10">
  <title>Nexus · Trading</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #080f1a;
      color: #e2e8f0;
      padding: 20px;
      min-height: 100vh;
    }}
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .header-left h1 {{
      font-size: 1.4rem;
      font-weight: 800;
      color: #f8fafc;
      letter-spacing: -0.02em;
    }}
    .header-left .sub {{
      color: #475569;
      font-size: 0.8rem;
      margin-top: 2px;
    }}
    .mode-badge {{
      background: #1e3a5f;
      color: #60a5fa;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      letter-spacing: .06em;
      text-transform: uppercase;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 16px;
    }}
    .card .label {{
      font-size: 0.7rem;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: .07em;
      margin-bottom: 6px;
    }}
    .card .value {{
      font-size: 1.55rem;
      font-weight: 800;
      color: #f1f5f9;
      line-height: 1;
    }}
    .card .sub-value {{
      font-size: 0.75rem;
      color: #475569;
      margin-top: 4px;
    }}
    .open-trade {{
      background: #0f2027;
      border: 1px solid #0ea5e9;
      border-radius: 12px;
      padding: 14px 18px;
      margin-bottom: 16px;
    }}
    .ot-label {{
      font-size: 0.72rem;
      font-weight: 700;
      color: #0ea5e9;
      letter-spacing: .07em;
      margin-bottom: 8px;
    }}
    .ot-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 0.88rem;
    }}
    .section {{
      background: #111827;
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 14px;
    }}
    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
    }}
    .section h2 {{
      font-size: 0.75rem;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .section-meta {{
      font-size: 0.75rem;
      color: #334155;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    th {{
      text-align: left;
      color: #475569;
      font-weight: 600;
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: .05em;
      padding: 6px 10px;
      border-bottom: 1px solid #1e293b;
    }}
    td {{ padding: 9px 10px; border-bottom: 1px solid #0f172a; color: #cbd5e1; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #0f172a; }}
    pre {{
      font-size: 0.8rem;
      color: #64748b;
      white-space: pre-wrap;
      font-family: 'SF Mono', 'Fira Code', monospace;
      line-height: 1.6;
    }}
    .dot {{
      display: inline-block;
      width: 7px; height: 7px;
      border-radius: 50%;
      background: #22c55e;
      margin-right: 6px;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{ 0%,100%{{opacity:1;transform:scale(1)}} 50%{{opacity:.5;transform:scale(0.85)}} }}
    .badge {{
      font-size: 0.68rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 10px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .badge-tv {{ background: #1e3a5f; color: #60a5fa; }}
    .badge-rsi {{ background: #1a2e1a; color: #4ade80; }}
    .hyp-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
    }}
    .hyp-label {{
      display: block;
      font-size: 0.68rem;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: .06em;
      margin-bottom: 3px;
    }}
    .hyp-val {{
      font-size: 0.88rem;
      color: #e2e8f0;
      font-weight: 600;
    }}
    canvas {{ width: 100%; height: 60px; display: block; }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }}
    @media (max-width: 640px) {{
      .two-col {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>

  <div class="header">
    <div class="header-left">
      <h1><span class="dot"></span>Nexus <span style="color:#475569;font-weight:400;font-size:0.9rem">/ trading</span></h1>
      <div class="sub">BTC/USDT · refreshes every 10s · last tick: {_fmt_ts(last_tick)}</div>
    </div>
    <div class="mode-badge">paper mode</div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="label">BTC Price</div>
      <div class="value">{_fmt_price(price)}</div>
    </div>
    <div class="card">
      <div class="label">Score</div>
      <div class="value" style="color:{score_color}">{_fmt_pct(score) if isinstance(score,(int,float)) else '—'}</div>
    </div>
    <div class="card">
      <div class="label">Total PnL</div>
      <div class="value" style="color:{'#22c55e' if total_pnl>0 else '#ef4444' if total_pnl<0 else '#94a3b8'}">{_fmt_pct(total_pnl) if closed else '—'}</div>
    </div>
    <div class="card">
      <div class="label">Win Rate</div>
      <div class="value">{win_rate}</div>
      <div class="sub-value">{len(wins)}W / {len(losses)}L</div>
    </div>
    <div class="card">
      <div class="label">Trades</div>
      <div class="value">{trade_count}</div>
      <div class="sub-value">strategy v{version}</div>
    </div>
    <div class="card">
      <div class="label">Best / Worst</div>
      <div class="value" style="font-size:1rem;margin-top:4px">
        <span style="color:#22c55e">{_fmt_pct(best)}</span>
        <span style="color:#475569"> / </span>
        <span style="color:#ef4444">{_fmt_pct(worst)}</span>
      </div>
    </div>
  </div>

  {open_trade_html}

  <div class="section">
    <div class="section-header">
      <h2>PnL per trade</h2>
      <span class="section-meta">last {len(pnl_data)} closed</span>
    </div>
    <canvas id="sparkline"></canvas>
  </div>

  <div class="section">
    <div class="section-header">
      <h2>Recent Trades</h2>
      <span class="section-meta">showing last 25</span>
    </div>
    {"<p style='color:#475569;font-size:0.85rem'>No trades yet — waiting for RSI entry signal.</p>" if not rows else
     f"<table><thead><tr><th>Entry</th><th>Dir</th><th>Entry $</th><th>Exit $</th><th>PnL</th><th>Reason</th><th>Strat</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table>"}
  </div>

  <div class="two-col">
    <div class="section">
      <div class="section-header"><h2>Last Reflection</h2></div>
      {hyp_html}
    </div>
    <div class="section">
      <div class="section-header"><h2>Current Strategy</h2></div>
      <pre>{strategy}</pre>
    </div>
  </div>

  <script>
    const data = {pnl_json};
    const canvas = document.getElementById('sparkline');
    if (canvas && data.length > 1) {{
      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = 60 * dpr;
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      const w = canvas.offsetWidth, h = 60;
      const min = Math.min(...data), max = Math.max(...data);
      const range = max - min || 1;
      const pad = 6;
      const step = (w - pad * 2) / (data.length - 1);

      ctx.beginPath();
      data.forEach((v, i) => {{
        const x = pad + i * step;
        const y = h - pad - ((v - min) / range) * (h - pad * 2);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }});
      ctx.strokeStyle = '#0AAAFF';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      data.forEach((v, i) => {{
        const x = pad + i * step;
        const y = h - pad - ((v - min) / range) * (h - pad * 2);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = v >= 0 ? '#22c55e' : '#ef4444';
        ctx.fill();
      }});
    }}
  </script>

</body>
</html>"""
    return html


@app.post("/webhook")
async def tradingview_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")
    action = payload.get("action", "").lower()
    if action not in ("buy", "sell", "close"):
        raise HTTPException(status_code=400, detail=f"unknown action: {action}")
    signal = {
        "action": action,
        "price": payload.get("price"),
        "indicator": payload.get("indicator", "tradingview"),
        "ts": datetime.now(timezone.utc).isoformat(),
        "raw": payload,
    }
    (STATE / "tv_signal.json").write_text(json.dumps(signal))
    return {"ok": True, "action": action}


@app.post("/reflect")
async def trigger_reflect(mode: str = "fallback"):
    if mode not in ("fallback", "hermes"):
        raise HTTPException(status_code=400, detail="mode must be fallback or hermes")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "hermes_trading.reflect", f"--{mode}"],
            capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parent.parent)},
        )
        return {"ok": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="reflect timed out")
