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
    return HTMLResponse(content=_DASHBOARD_HTML)


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus · Trading</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #080f1a; color: #e2e8f0; min-height: 100vh; }
    #app { max-width: 1200px; margin: 0 auto; padding: 20px; }

    /* Header */
    .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 8px; }
    .header-left h1 { font-size: 1.4rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em; }
    .header-left .sub { color: #475569; font-size: 0.8rem; margin-top: 2px; }
    .header-right { display: flex; align-items: center; gap: 10px; }
    .mode-badge { background: #1e3a5f; color: #0AAAFF; font-size: 0.7rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; letter-spacing: .06em; text-transform: uppercase; }
    .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #22c55e; margin-right: 6px; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(0.8)} }

    /* Stat grid */
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 14px; }
    .stat { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 14px 16px; }
    .stat .lbl { font-size: 0.68rem; color: #475569; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; }
    .stat .val { font-size: 1.5rem; font-weight: 800; color: #f1f5f9; line-height: 1; }
    .stat .sub { font-size: 0.72rem; color: #475569; margin-top: 3px; }

    /* Live trade */
    .live-trade { background: linear-gradient(135deg, #0a1f35 0%, #0d1a2e 100%); border: 1px solid #0AAAFF; border-radius: 14px; padding: 18px 20px; margin-bottom: 14px; }
    .live-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
    .live-pill { background: #0AAAFF22; color: #0AAAFF; font-size: 0.68rem; font-weight: 800; padding: 3px 10px; border-radius: 20px; letter-spacing: .08em; text-transform: uppercase; }
    .live-pulse { width: 8px; height: 8px; border-radius: 50%; background: #0AAAFF; animation: pulse 1.5s infinite; }
    .live-body { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
    .live-item .lbl { font-size: 0.68rem; color: #475569; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
    .live-item .val { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }

    /* Card */
    .card { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 16px 18px; margin-bottom: 14px; }
    .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
    .card-header h2 { font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; }
    .card-meta { font-size: 0.72rem; color: #334155; }

    /* Chart */
    canvas { width: 100%; display: block; }

    /* Table */
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
    th { text-align: left; color: #475569; font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: .05em; padding: 7px 10px; border-bottom: 1px solid #1e293b; white-space: nowrap; }
    td { padding: 10px 10px; border-bottom: 1px solid #0f172a; color: #cbd5e1; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #0f172a44; }
    .pnl-positive { color: #22c55e; font-weight: 700; }
    .pnl-negative { color: #ef4444; font-weight: 700; }
    .pnl-neutral { color: #94a3b8; }
    .badge { font-size: 0.65rem; font-weight: 700; padding: 2px 7px; border-radius: 8px; text-transform: uppercase; letter-spacing: .04em; }
    .badge-tv { background: #1e3a5f33; color: #0AAAFF; border: 1px solid #0AAAFF44; }
    .badge-rsi { background: #1a2e1a; color: #4ade80; border: 1px solid #4ade8033; }
    .badge-open { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b33; }
    .dir-long { color: #22c55e; font-weight: 600; font-size: 0.75rem; }
    .dir-short { color: #ef4444; font-weight: 600; font-size: 0.75rem; }

    /* Two col */
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 700px) { .two-col { grid-template-columns: 1fr; } }

    /* Strategy */
    pre { font-size: 0.78rem; color: #64748b; white-space: pre-wrap; font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.7; }

    /* Reflection */
    .hyp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
    .hyp-item .lbl { font-size: 0.65rem; color: #475569; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .hyp-item .val { font-size: 0.85rem; color: #e2e8f0; font-weight: 600; }

    /* Empty state */
    .empty { text-align: center; padding: 32px 20px; color: #475569; font-size: 0.85rem; }
    .empty strong { display: block; color: #64748b; margin-bottom: 6px; font-size: 1rem; }

    /* Loading */
    #loading { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #080f1a; display: flex; align-items: center; justify-content: center; z-index: 100; }
    .spinner { width: 36px; height: 36px; border: 3px solid #1e293b; border-top-color: #0AAAFF; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

<div id="loading"><div class="spinner"></div></div>

<div id="app" style="display:none">
  <div class="header">
    <div class="header-left">
      <h1><span class="dot"></span>Nexus <span style="color:#475569;font-weight:400;font-size:0.9rem">/ trading</span></h1>
      <div class="sub" id="sub-text">BTC/USDT · paper mode · loading...</div>
    </div>
    <div class="header-right">
      <div class="mode-badge" id="mode-badge">paper</div>
    </div>
  </div>

  <!-- Stats -->
  <div class="stat-grid">
    <div class="stat"><div class="lbl">BTC Price</div><div class="val" id="s-price">—</div></div>
    <div class="stat"><div class="lbl">Total PnL</div><div class="val" id="s-pnl">—</div></div>
    <div class="stat"><div class="lbl">Win Rate</div><div class="val" id="s-wr">—</div><div class="sub" id="s-wl">—</div></div>
    <div class="stat"><div class="lbl">Closed Trades</div><div class="val" id="s-trades">—</div><div class="sub" id="s-strat">—</div></div>
    <div class="stat"><div class="lbl">Best Trade</div><div class="val pnl-positive" id="s-best">—</div></div>
    <div class="stat"><div class="lbl">Worst Trade</div><div class="val pnl-negative" id="s-worst">—</div></div>
  </div>

  <!-- Live open trade -->
  <div class="live-trade" id="live-trade" style="display:none">
    <div class="live-header">
      <div class="live-pulse"></div>
      <span class="live-pill">Live Trade Open</span>
      <span style="color:#475569;font-size:0.75rem" id="lt-since"></span>
    </div>
    <div class="live-body">
      <div class="live-item"><div class="lbl">Asset</div><div class="val" id="lt-asset">—</div></div>
      <div class="live-item"><div class="lbl">Direction</div><div class="val" id="lt-dir">—</div></div>
      <div class="live-item"><div class="lbl">Entry Price</div><div class="val" id="lt-entry">—</div></div>
      <div class="live-item"><div class="lbl">Current Price</div><div class="val" id="lt-cur">—</div></div>
      <div class="live-item"><div class="lbl">Live PnL</div><div class="val" id="lt-pnl">—</div></div>
      <div class="live-item"><div class="lbl">Strategy</div><div class="val" id="lt-strat">—</div></div>
    </div>
  </div>

  <!-- Cumulative PnL chart -->
  <div class="card" id="chart-card" style="display:none">
    <div class="card-header">
      <h2>Cumulative PnL</h2>
      <span class="card-meta" id="chart-meta"></span>
    </div>
    <canvas id="chart" height="80"></canvas>
  </div>

  <!-- Trade history -->
  <div class="card">
    <div class="card-header">
      <h2>Trade History</h2>
      <span class="card-meta" id="trade-meta"></span>
    </div>
    <div class="table-wrap" id="trade-table">
      <div class="empty"><strong>No closed trades yet</strong>Waiting for RSI &lt; 30 entry signal on BTC/USDT</div>
    </div>
  </div>

  <!-- Strategy + Reflection -->
  <div class="two-col">
    <div class="card">
      <div class="card-header"><h2>Last Reflection</h2></div>
      <div id="reflection-body"><div class="empty">No reflections yet — fires after 5 closed trades.</div></div>
    </div>
    <div class="card">
      <div class="card-header"><h2>Current Strategy</h2></div>
      <pre id="strategy-pre">Loading...</pre>
    </div>
  </div>
</div>

<script>
const fmt = (n) => n == null ? '—' : '$' + Number(n).toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0});
const fmtPct = (n) => n == null ? '—' : (n >= 0 ? '+' : '') + (n * 100).toFixed(3) + '%';
const fmtTs = (s) => s ? s.slice(0,16).replace('T',' ') : '—';

let lastTradeCount = -1;
let allTrades = [];
let statusData = {};

async function fetchAll() {
  const [status, trades] = await Promise.all([
    fetch('/status').then(r => r.json()),
    fetch('/trades').then(r => r.json())
  ]);
  statusData = status;
  allTrades = trades;
  render(status, trades);
}

function render(status, trades) {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('app').style.display = '';

  const price = status.last_price;
  const closed = trades.filter(t => t.pnl_pct != null);
  const wins = closed.filter(t => t.pnl_pct > 0);
  const totalPnl = closed.reduce((s, t) => s + t.pnl_pct, 0);
  const best = closed.length ? Math.max(...closed.map(t => t.pnl_pct)) : null;
  const worst = closed.length ? Math.min(...closed.map(t => t.pnl_pct)) : null;

  // Subtext
  document.getElementById('sub-text').textContent =
    `BTC/USDT · paper mode · last tick: ${fmtTs(status.last_tick)} · ${status.consecutive_failures > 0 ? status.consecutive_failures + ' failures' : 'healthy'}`;

  // Stats
  document.getElementById('s-price').textContent = fmt(price);
  const pnlEl = document.getElementById('s-pnl');
  pnlEl.textContent = closed.length ? fmtPct(totalPnl) : '—';
  pnlEl.className = 'val ' + (totalPnl > 0 ? 'pnl-positive' : totalPnl < 0 ? 'pnl-negative' : 'pnl-neutral');
  document.getElementById('s-wr').textContent = closed.length ? Math.round(wins.length / closed.length * 100) + '%' : '—';
  document.getElementById('s-wl').textContent = closed.length ? `${wins.length}W / ${closed.length - wins.length}L` : '';
  document.getElementById('s-trades').textContent = closed.length;

  // Strategy version
  let ver = '—';
  if (status.strategy) { const m = status.strategy.match(/version:\\s*"?(\\d+)"?/); if (m) ver = 'v' + m[1]; }
  document.getElementById('s-strat').textContent = 'strategy ' + ver;
  document.getElementById('s-best').textContent = best != null ? fmtPct(best) : '—';
  document.getElementById('s-worst').textContent = worst != null ? fmtPct(worst) : '—';

  // Open trade
  const ot = status.open_trade;
  const liveDiv = document.getElementById('live-trade');
  if (ot) {
    liveDiv.style.display = '';
    const entry = ot.entry_price || 0;
    const cur = price || entry;
    const livePnl = entry ? (cur - entry) / entry : 0;
    document.getElementById('lt-since').textContent = 'since ' + fmtTs(ot.entry_ts);
    document.getElementById('lt-asset').textContent = ot.asset || 'BTC/USDT';
    const dirEl = document.getElementById('lt-dir');
    dirEl.textContent = (ot.direction || '').toUpperCase();
    dirEl.className = 'val ' + (ot.direction === 'long' ? 'pnl-positive' : 'pnl-negative');
    document.getElementById('lt-entry').textContent = fmt(entry);
    document.getElementById('lt-cur').textContent = fmt(cur);
    const pEl = document.getElementById('lt-pnl');
    pEl.textContent = fmtPct(livePnl);
    pEl.className = 'val ' + (livePnl >= 0 ? 'pnl-positive' : 'pnl-negative');
    document.getElementById('lt-strat').textContent = 'v' + (ot.strategy_version || '?');
  } else {
    liveDiv.style.display = 'none';
  }

  // Chart — cumulative PnL line
  const chartCard = document.getElementById('chart-card');
  if (closed.length > 1) {
    chartCard.style.display = '';
    document.getElementById('chart-meta').textContent = `${closed.length} closed trades`;
    drawChart(closed);
  } else {
    chartCard.style.display = 'none';
  }

  // Trade table
  const tableDiv = document.getElementById('trade-table');
  document.getElementById('trade-meta').textContent = closed.length ? `${closed.length} closed · showing all` : '';
  if (closed.length === 0 && !ot) {
    tableDiv.innerHTML = '<div class="empty"><strong>No closed trades yet</strong>Waiting for RSI &lt; 30 entry signal on BTC/USDT</div>';
  } else {
    const allRows = [...closed].reverse();
    // Add open trade as first row if exists
    const openRow = ot ? [{
      entry_ts: ot.entry_ts, direction: ot.direction, entry_price: ot.entry_price,
      exit_price: price, pnl_pct: ot.entry_price ? (price - ot.entry_price) / ot.entry_price : null,
      exit_reason: 'open', strategy_version: ot.strategy_version, source: ot.source, _open: true
    }] : [];
    const rows = [...openRow, ...allRows].map(t => {
      const pnl = t.pnl_pct;
      const pnlClass = t._open ? 'pnl-neutral' : (pnl > 0 ? 'pnl-positive' : pnl < 0 ? 'pnl-negative' : 'pnl-neutral');
      const pnlStr = t._open
        ? `<span class="${pnlClass}">${fmtPct(pnl)} <span class="badge badge-open">live</span></span>`
        : `<span class="${pnlClass}">${fmtPct(pnl)}</span>`;
      const src = t.source || 'rsi';
      const srcBadge = `<span class="badge ${src === 'tradingview' ? 'badge-tv' : 'badge-rsi'}">${src}</span>`;
      const dirClass = t.direction === 'long' ? 'dir-long' : 'dir-short';
      return `<tr>
        <td>${fmtTs(t.entry_ts)}</td>
        <td><span class="${dirClass}">${(t.direction||'').toUpperCase()}</span></td>
        <td>${fmt(t.entry_price)}</td>
        <td>${t._open ? '<span style="color:#f59e0b">open</span>' : fmt(t.exit_price)}</td>
        <td>${pnlStr}</td>
        <td style="color:#64748b;font-size:0.78rem">${t.exit_reason || '—'}</td>
        <td style="color:#475569;font-size:0.75rem">v${t.strategy_version || '?'}</td>
        <td>${srcBadge}</td>
      </tr>`;
    }).join('');
    tableDiv.innerHTML = `<table><thead><tr>
      <th>Entry Time</th><th>Dir</th><th>Entry $</th><th>Exit $</th><th>PnL</th><th>Reason</th><th>Strat</th><th>Source</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
  }

  // Strategy
  document.getElementById('strategy-pre').textContent = status.strategy || '—';

  // Reflection
  const hyp = status.last_hypothesis;
  const refDiv = document.getElementById('reflection-body');
  if (hyp) {
    refDiv.innerHTML = `
      <div class="hyp-grid">
        <div class="hyp-item"><div class="lbl">Mode</div><div class="val">${hyp.mode || '—'}</div></div>
        <div class="hyp-item"><div class="lbl">Version</div><div class="val">v${hyp.version || '?'}</div></div>
        <div class="hyp-item"><div class="lbl">Changed</div><div class="val">${hyp.changed || '—'}</div></div>
        <div class="hyp-item"><div class="lbl">Score before</div><div class="val">${hyp.score_before != null ? hyp.score_before.toFixed(3) : '—'}</div></div>
      </div>
      <p style="color:#94a3b8;font-size:0.82rem;margin-top:10px;line-height:1.5">${hyp.rationale || ''}</p>`;
  } else {
    refDiv.innerHTML = '<div class="empty">No reflections yet — fires after 5 closed trades.</div>';
  }
}

function drawChart(closed) {
  const canvas = document.getElementById('chart');
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.offsetWidth * dpr;
  canvas.height = 80 * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const W = canvas.offsetWidth, H = 80;
  const pad = { l: 48, r: 12, t: 8, b: 8 };

  // Build cumulative line
  let cum = 0;
  const points = closed.map((t, i) => { cum += t.pnl_pct * 100; return { x: i, y: cum }; });
  const xs = points.map(p => p.x), ys = points.map(p => p.y);
  const minY = Math.min(0, ...ys), maxY = Math.max(0, ...ys);
  const range = maxY - minY || 1;
  const toX = (i) => pad.l + (i / (points.length - 1 || 1)) * (W - pad.l - pad.r);
  const toY = (v) => pad.t + (1 - (v - minY) / range) * (H - pad.t - pad.b);

  // Zero line
  const zeroY = toY(0);
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad.l, zeroY); ctx.lineTo(W - pad.r, zeroY); ctx.stroke();

  // Fill area
  const finalY = cum >= 0;
  ctx.beginPath();
  ctx.moveTo(toX(0), toY(0));
  points.forEach(p => ctx.lineTo(toX(p.x), toY(p.y)));
  ctx.lineTo(toX(points.length - 1), toY(0));
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, pad.t, 0, H);
  if (finalY) {
    grad.addColorStop(0, '#0AAAFF33'); grad.addColorStop(1, '#0AAAFF05');
  } else {
    grad.addColorStop(0, '#ef444405'); grad.addColorStop(1, '#ef444433');
  }
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  points.forEach((p, i) => i === 0 ? ctx.moveTo(toX(p.x), toY(p.y)) : ctx.lineTo(toX(p.x), toY(p.y)));
  ctx.strokeStyle = cum >= 0 ? '#0AAAFF' : '#ef4444';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Y axis labels
  ctx.fillStyle = '#475569';
  ctx.font = `${10 * dpr / dpr}px system-ui`;
  ctx.textAlign = 'right';
  ctx.fillText((maxY >= 0 ? '+' : '') + maxY.toFixed(2) + '%', pad.l - 4, pad.t + 8);
  ctx.fillText((minY >= 0 ? '+' : '') + minY.toFixed(2) + '%', pad.l - 4, H - pad.b);

  // End dot
  const last = points[points.length - 1];
  ctx.beginPath();
  ctx.arc(toX(last.x), toY(last.y), 4, 0, Math.PI * 2);
  ctx.fillStyle = cum >= 0 ? '#0AAAFF' : '#ef4444';
  ctx.fill();
}

// Refresh every 10s
fetchAll();
setInterval(fetchAll, 10000);
</script>
</body>
</html>"""


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
