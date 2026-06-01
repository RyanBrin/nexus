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
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "—"


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


# ── Stock endpoints ───────────────────────────────────────────────────────────

@app.get("/stocks/watchlist")
async def get_watchlist():
    from hermes_trading.stocks.watchlist import load_watchlist
    return [s.to_dict() for s in load_watchlist()]


@app.post("/stocks/watchlist")
async def add_stock(request: Request):
    from hermes_trading.stocks.watchlist import upsert_stock, StockEntry
    data = await request.json()
    ticker = data.get("ticker", "").upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")
    stock = StockEntry(
        ticker=ticker,
        company_name=data.get("company_name", ""),
        trading_enabled=data.get("trading_enabled", False),
    )
    upsert_stock(stock)
    return {"ok": True, "ticker": ticker}


@app.delete("/stocks/watchlist/{ticker}")
async def remove_stock(ticker: str):
    from hermes_trading.stocks.watchlist import remove_stock as _remove
    ok = _remove(ticker.upper())
    if not ok:
        raise HTTPException(status_code=404, detail="ticker not found")
    return {"ok": True}


@app.patch("/stocks/watchlist/{ticker}/toggle")
async def toggle_stock(ticker: str, request: Request):
    from hermes_trading.stocks.watchlist import toggle_trading
    data = await request.json()
    enabled = bool(data.get("enabled", False))
    ok = toggle_trading(ticker.upper(), enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="ticker not found")
    return {"ok": True, "enabled": enabled}


@app.get("/stocks/trades")
async def stock_trades():
    from hermes_trading.stocks.loop import _load_stock_trades
    return _load_stock_trades()


@app.get("/stocks/logs")
async def stock_logs():
    from hermes_trading.stocks.reflect import load_stock_logs
    return load_stock_logs(50)


@app.get("/strategy/list")
async def strategy_list():
    from hermes_trading.strategy_registry import list_strategies, bootstrap_from_existing
    bootstrap_from_existing()
    return list_strategies()


@app.get("/strategy/active")
async def strategy_active():
    from hermes_trading.strategy_registry import get_active_strategy_name, load_strategy_meta, load_strategy_params
    name = get_active_strategy_name()
    return {
        "name": name,
        "meta": load_strategy_meta(name) or {},
        "params": load_strategy_params(name) or {},
    }


@app.post("/strategy/select/{name}")
async def strategy_select(name: str):
    from hermes_trading.strategy_registry import set_active_strategy, list_strategies
    names = [s["name"] for s in list_strategies()]
    if name not in names:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    set_active_strategy(name)
    return {"ok": True, "active": name}


@app.post("/strategy/lock/{name}")
async def strategy_lock(name: str):
    from hermes_trading.strategy_registry import lock_strategy
    lock_strategy(name)
    return {"ok": True, "locked": name}


@app.post("/strategy/unlock/{name}")
async def strategy_unlock(name: str):
    from hermes_trading.strategy_registry import unlock_strategy
    unlock_strategy(name)
    return {"ok": True, "unlocked": name}


@app.get("/strategy/performance")
async def strategy_performance():
    from hermes_trading import performance
    trades = await db.load_trades()
    return performance.calculate_all(trades)


@app.get("/strategy/phase")
async def strategy_phase():
    from hermes_trading import performance, strategy_registry
    from hermes_trading.phase_tracker import check_phase_progress
    trades = await db.load_trades()
    strategy_registry.bootstrap_from_existing()
    active_name = strategy_registry.get_active_strategy_name()
    perf = performance.calculate(active_name, trades)
    return check_phase_progress(perf.to_dict(), trades)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=_DASHBOARD_HTML)


def _build_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Nexus · Trading</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #080f1a; color: #e2e8f0; min-height: 100vh; }
    #app { max-width: 1400px; margin: 0 auto; padding: 20px; }

    /* Tab navigation — overflow hidden prevents -1px bleed */
    .tab-nav { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 1px solid #1e293b; flex-wrap: wrap; overflow: hidden; }
    .tab-btn { background: none; border: none; border-bottom: 2px solid transparent; color: #475569; font-size: 0.82rem; font-weight: 600; padding: 10px 18px; cursor: pointer; white-space: nowrap; transition: color 0.15s, border-color 0.15s; letter-spacing: .03em; flex-shrink: 0; }
    .tab-btn:hover { color: #94a3b8; background: #ffffff08; }
    .tab-btn.active { color: #0AAAFF; border-bottom-color: #0AAAFF; }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Header */
    .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
    .header-left h1 { font-size: 1.4rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em; }
    .header-left .sub { color: #475569; font-size: 0.8rem; margin-top: 2px; }
    .header-right { display: flex; align-items: center; gap: 10px; }
    .mode-badge { background: #1e3a5f; color: #0AAAFF; font-size: 0.7rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; letter-spacing: .06em; text-transform: uppercase; white-space: nowrap; }
    .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #22c55e; margin-right: 6px; flex-shrink: 0; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(0.8)} }

    /* Stat grid */
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 14px; }
    .stat { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 14px 16px; min-width: 0; }
    .stat .lbl { font-size: 0.68rem; color: #475569; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 5px; }
    .stat .val { font-size: 1.5rem; font-weight: 800; color: #f1f5f9; line-height: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .stat .sub { font-size: 0.72rem; color: #475569; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Live trade */
    .live-trade { background: linear-gradient(135deg, #0a1f35 0%, #0d1a2e 100%); border: 1px solid #0AAAFF; border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; overflow: hidden; }
    .live-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
    .live-pill { background: #0AAAFF22; color: #0AAAFF; font-size: 0.68rem; font-weight: 800; padding: 3px 10px; border-radius: 20px; letter-spacing: .08em; text-transform: uppercase; white-space: nowrap; }
    .live-pulse { width: 8px; height: 8px; border-radius: 50%; background: #0AAAFF; flex-shrink: 0; animation: pulse 1.5s infinite; }
    .live-body { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; }
    .live-item { min-width: 0; }
    .live-item .lbl { font-size: 0.65rem; color: #475569; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 3px; }
    .live-item .val { font-size: 1rem; font-weight: 700; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Card */
    .card { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 16px 18px; margin-bottom: 14px; overflow: hidden; }
    .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; gap: 8px; }
    .card-header h2 { font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; white-space: nowrap; }
    .card-meta { font-size: 0.72rem; color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Chart — explicit min-height prevents collapse */
    canvas { width: 100%; display: block; min-height: 60px; }

    /* Table */
    .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100%; border-collapse: collapse; font-size: 0.82rem; min-width: 480px; }
    th { text-align: left; color: #475569; font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: .05em; padding: 7px 10px; border-bottom: 1px solid #1e293b; white-space: nowrap; }
    td { padding: 10px; border-bottom: 1px solid #0f172a; color: #cbd5e1; vertical-align: middle; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #0f172a44; }
    .pnl-positive { color: #22c55e; font-weight: 700; }
    .pnl-negative { color: #ef4444; font-weight: 700; }
    .pnl-neutral { color: #94a3b8; }
    .badge { font-size: 0.65rem; font-weight: 700; padding: 2px 7px; border-radius: 8px; text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; }
    .badge-tv { background: #1e3a5f33; color: #0AAAFF; border: 1px solid #0AAAFF44; }
    .badge-rsi { background: #1a2e1a; color: #4ade80; border: 1px solid #4ade8033; }
    .badge-open { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b33; }
    .dir-long { color: #22c55e; font-weight: 600; font-size: 0.75rem; }

    /* Stock rows */
    .stock-grid { display: flex; flex-direction: column; gap: 10px; }
    .stock-row { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 14px 16px; overflow: hidden; }
    .stock-row.trading-on { border-color: #0AAAFF44; }
    .stock-row.in-trade { border-color: #22c55e88; }
    .stock-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; row-gap: 6px; }
    .stock-ticker { font-size: 1rem; font-weight: 800; color: #f8fafc; flex-shrink: 0; }
    .stock-name { font-size: 0.78rem; color: #475569; flex-shrink: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
    .stock-price { font-size: 1rem; font-weight: 700; color: #f1f5f9; margin-left: auto; flex-shrink: 0; }
    .stock-change { font-size: 0.78rem; font-weight: 600; flex-shrink: 0; }
    .stock-bottom { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px; margin-top: 4px; }
    .stock-field { min-width: 0; }
    .stock-field .lbl { font-size: 0.62rem; color: #475569; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .stock-field .val { font-size: 0.82rem; font-weight: 600; color: #cbd5e1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .stock-notes { margin-top: 10px; font-size: 0.78rem; color: #64748b; font-style: italic; line-height: 1.5; border-top: 1px solid #1e293b; padding-top: 8px; max-height: 80px; overflow-y: auto; word-break: break-word; }
    .toggle-btn { background: #1e293b; border: 1px solid #334155; color: #64748b; font-size: 0.68rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; cursor: pointer; text-transform: uppercase; letter-spacing: .06em; flex-shrink: 0; white-space: nowrap; }
    .toggle-btn.on { background: #0AAAFF22; border-color: #0AAAFF; color: #0AAAFF; }
    .add-stock-form { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
    .add-stock-form input { background: #111827; border: 1px solid #1e293b; color: #e2e8f0; padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; flex: 1; min-width: 80px; }
    .add-stock-form input:focus { outline: none; border-color: #0AAAFF; }
    .add-stock-form button { background: #0AAAFF; color: #080f1a; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 0.82rem; cursor: pointer; white-space: nowrap; flex-shrink: 0; }

    /* Signal badges */
    .sig { font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 8px; text-transform: uppercase; letter-spacing: .04em; white-space: nowrap; flex-shrink: 0; }
    .sig-entry  { background: #22c55e22; color: #22c55e; border: 1px solid #22c55e44; }
    .sig-watch  { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b44; }
    .sig-wait   { background: #0AAAFF22; color: #0AAAFF; border: 1px solid #0AAAFF44; }
    .sig-none   { background: #47556922; color: #475569; border: 1px solid #47556944; }
    .sig-invalid{ background: #ef444422; color: #ef4444; border: 1px solid #ef444444; }

    /* Asset type badges */
    .asset-btc  { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b33; }
    .asset-stock{ background: #0AAAFF22; color: #0AAAFF; border: 1px solid #0AAAFF33; }

    /* Log entries */
    .log-entry { background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; overflow: hidden; }
    .log-header { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; flex-wrap: wrap; row-gap: 4px; }
    .log-header span[style*="margin-left:auto"] { margin-left: auto !important; flex-shrink: 0; }
    .log-reasoning { font-size: 0.8rem; color: #94a3b8; line-height: 1.5; word-break: break-word; }

    /* Two-column layout — collapses at 640px */
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 700px) { .two-col { grid-template-columns: 1fr; } }

    /* Overview two-col — also collapses */
    .ov-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
    @media (max-width: 640px) { .ov-grid { grid-template-columns: 1fr; } }

    /* Strategy pre */
    pre { font-size: 0.78rem; color: #64748b; white-space: pre-wrap; word-break: break-word; font-family: 'SF Mono', 'Fira Code', monospace; line-height: 1.7; }

    /* Reflection grid */
    .hyp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
    @media (max-width: 500px) { .hyp-grid { grid-template-columns: 1fr; } }
    .hyp-item .lbl { font-size: 0.65rem; color: #475569; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2px; }
    .hyp-item .val { font-size: 0.85rem; color: #e2e8f0; font-weight: 600; }

    /* Empty / loading states */
    .empty { text-align: center; padding: 32px 20px; color: #475569; font-size: 0.85rem; }
    .empty strong { display: block; color: #64748b; margin-bottom: 6px; font-size: 1rem; }
    #loading { position: fixed; inset: 0; background: #080f1a; display: flex; align-items: center; justify-content: center; z-index: 100; }
    .spinner { width: 36px; height: 36px; border: 3px solid #1e293b; border-top-color: #0AAAFF; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
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
      <div class="sub" id="sub-text">loading...</div>
    </div>
    <div class="header-right">
      <div class="mode-badge" id="mode-badge">paper</div>
    </div>
  </div>

  <!-- Tab navigation -->
  <div class="tab-nav">
    <button class="tab-btn active" onclick="showTab('overview',this)">Overview</button>
    <button class="tab-btn" onclick="showTab('btc',this)">BTC Bot</button>
    <button class="tab-btn" onclick="showTab('stocks',this)">Stocks</button>
    <button class="tab-btn" onclick="showTab('active',this)">Active Trades</button>
    <button class="tab-btn" onclick="showTab('strategy',this)">Strategies</button>
    <button class="tab-btn" onclick="showTab('logs',this)">Logs</button>
  </div>

  <!-- ══ OVERVIEW TAB ══ -->
  <div class="tab-pane active" id="tab-overview">
    <div class="ov-grid">
      <!-- BTC summary -->
      <div class="card">
        <div class="card-header"><h2>BTC Bot</h2><span class="card-meta" id="btc-status-label">loading</span></div>
        <div class="stat-grid" style="margin-bottom:0">
          <div class="stat"><div class="lbl">BTC Price</div><div class="val" id="ov-price">—</div></div>
          <div class="stat"><div class="lbl">Total PnL</div><div class="val" id="ov-pnl">—</div></div>
          <div class="stat"><div class="lbl">Win Rate</div><div class="val" id="ov-wr">—</div></div>
          <div class="stat"><div class="lbl">Trades</div><div class="val" id="ov-trades">—</div></div>
        </div>
      </div>
      <!-- Stocks summary -->
      <div class="card">
        <div class="card-header"><h2>Stock Watchlist</h2><span class="card-meta" id="stock-status-label">loading</span></div>
        <div class="stat-grid" style="margin-bottom:0">
          <div class="stat"><div class="lbl">Watching</div><div class="val" id="ov-watching">—</div></div>
          <div class="stat"><div class="lbl">Active</div><div class="val" id="ov-enabled">—</div></div>
          <div class="stat"><div class="lbl">In Trade</div><div class="val" id="ov-in-trade">—</div></div>
          <div class="stat"><div class="lbl">Stock PnL</div><div class="val" id="ov-spnl">—</div></div>
        </div>
      </div>
    </div>
    <!-- Live BTC trade on overview -->
    <div id="ov-live-trade"></div>
    <!-- Phase progress -->
    <div class="card" id="phase-card">
      <div class="card-header"><h2>Phase Progress</h2><span class="card-meta" id="phase-label">loading...</span></div>
      <div id="phase-body"><div class="empty">Loading phase data...</div></div>
    </div>
  </div>

  <!-- ══ BTC BOT TAB ══ -->
  <div class="tab-pane" id="tab-btc">
    <!-- Stats -->
    <div class="stat-grid">
      <div class="stat"><div class="lbl">BTC Price</div><div class="val" id="s-price">—</div></div>
      <div class="stat"><div class="lbl">Total PnL</div><div class="val" id="s-pnl">—</div></div>
      <div class="stat"><div class="lbl">Win Rate</div><div class="val" id="s-wr">—</div><div class="sub" id="s-wl">—</div></div>
      <div class="stat"><div class="lbl">Closed Trades</div><div class="val" id="s-trades">—</div><div class="sub" id="s-strat">—</div></div>
      <div class="stat"><div class="lbl">Best Trade</div><div class="val pnl-positive" id="s-best">—</div></div>
      <div class="stat"><div class="lbl">Worst Trade</div><div class="val pnl-negative" id="s-worst">—</div></div>
    </div>
    <div class="live-trade" id="live-trade" style="display:none">
      <div class="live-header">
        <div class="live-pulse"></div>
        <span class="live-pill">Live BTC Trade</span>
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
    <div class="card" id="chart-card" style="display:none">
      <div class="card-header"><h2>Cumulative PnL</h2><span class="card-meta" id="chart-meta"></span></div>
      <canvas id="chart" height="80"></canvas>
    </div>
    <div class="card">
      <div class="card-header"><h2>Trade History</h2><span class="card-meta" id="trade-meta"></span></div>
      <div class="table-wrap" id="trade-table"><div class="empty" id="empty-state"><strong>No closed trades yet</strong>Waiting for entry signal</div></div>
    </div>
    <div class="two-col">
      <div class="card"><div class="card-header"><h2>Last BTC Reflection</h2></div><div id="reflection-body"><div class="empty">No reflections yet.</div></div></div>
      <div class="card"><div class="card-header"><h2>Current BTC Strategy</h2></div><pre id="strategy-pre">Loading...</pre></div>
    </div>
  </div>

  <!-- ══ STOCKS TAB ══ -->
  <div class="tab-pane" id="tab-stocks">
    <div class="add-stock-form">
      <input id="new-ticker" placeholder="Ticker (e.g. AAPL)" style="max-width:140px"/>
      <input id="new-name" placeholder="Company name (optional)"/>
      <button onclick="addStock()">+ Add</button>
    </div>
    <div class="stock-grid" id="stock-list">
      <div class="empty"><strong>Loading watchlist...</strong></div>
    </div>
  </div>

  <!-- ══ ACTIVE TRADES TAB ══ -->
  <div class="tab-pane" id="tab-active">
    <div class="card">
      <div class="card-header"><h2>All Active Positions</h2><span class="card-meta" id="active-meta"></span></div>
      <div id="active-trades-body"><div class="empty">No active positions.</div></div>
    </div>
    <div class="card" style="margin-top:14px">
      <div class="card-header"><h2>Recent Closed Trades — All Assets</h2></div>
      <div class="table-wrap" id="all-trades-table"><div class="empty">No closed trades yet.</div></div>
    </div>
  </div>

  <!-- ══ STRATEGY LOGS TAB ══ -->
  <div class="tab-pane" id="tab-logs">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
      <div>
        <div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">BTC Reflections</div>
        <div id="btc-logs"><div class="empty">No BTC logs yet.</div></div>
      </div>
      <div>
        <div style="font-size:0.72rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">Stock Analysis Logs</div>
        <div id="stock-logs"><div class="empty">No stock logs yet.</div></div>
      </div>
    </div>
  </div>

  <!-- ══ OLD HIDDEN STAT IDs (keep for JS compat) ══ -->
  <span id="btc-sub" style="display:none"></span>

  <!-- Stats (shown on overview) -->
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
      <div class="empty" id="empty-state"><strong>No closed trades yet</strong>Waiting for entry signal on BTC/USDT</div>
    </div>
  </div>

  <!-- Strategy + Reflection -->
  <div class="two-col">
    <div class="card">
      <div class="card-header"><h2>Last Reflection</h2></div>
      <div id="reflection-body"><div class="empty">No reflections yet — fires after 25 closed trades.</div></div>
    </div>
    <div class="card">
      <div class="card-header"><h2>Current Strategy</h2></div>
      <pre id="strategy-pre">Loading...</pre>
    </div>
  </div>
</div>

<!-- ══ STRATEGY SELECTOR TAB ══ -->
<div class="tab-pane" id="tab-strategy">
  <div class="card">
    <div class="card-header">
      <h2>Strategy Selector</h2>
      <span class="card-meta" id="strat-active-label">loading...</span>
    </div>
    <div id="strategy-list"><div class="empty">Loading strategies...</div></div>
  </div>
  <div class="card">
    <div class="card-header"><h2>Performance by Strategy</h2><span class="card-meta">expectancy = edge</span></div>
    <div id="perf-table"><div class="empty">No performance data yet.</div></div>
  </div>
  <div class="card">
    <div class="card-header"><h2>What is Expectancy?</h2></div>
    <p style="font-size:0.82rem;color:#94a3b8;line-height:1.6">
      <strong style="color:#e2e8f0">Expectancy</strong> = (Win Rate × Avg Win) − (Loss Rate × Avg Loss)<br>
      A <strong style="color:#22c55e">positive expectancy</strong> means the strategy has edge over time.<br>
      <strong style="color:#f59e0b">Data quality:</strong> insufficient &lt;25 trades · early signal 25–50 · useful 50–100 · reliable 100+<br>
      <strong style="color:#ef4444">Lock a strategy</strong> once it proves positive expectancy — don't let Claude change what's working.
    </p>
  </div>
</div>

<script>
const fmt = (n) => n == null ? '—' : '$' + Number(n).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
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

  // Overview tab BTC stats
  document.getElementById('ov-price').textContent = fmt(price);
  const ovPnlEl = document.getElementById('ov-pnl');
  ovPnlEl.textContent = closed.length ? fmtPct(totalPnl) : '—';
  ovPnlEl.className = 'val ' + (totalPnl > 0 ? 'pnl-positive' : totalPnl < 0 ? 'pnl-negative' : 'pnl-neutral');
  document.getElementById('ov-wr').textContent = closed.length ? Math.round(wins.length / closed.length * 100) + '%' : '—';
  document.getElementById('ov-trades').textContent = closed.length;
  document.getElementById('btc-status-label').textContent = `${status.status} · ${fmtTs(status.last_tick)}`;

  // Overview live trade card (duplicate of BTC tab)
  const ovLive = document.getElementById('ov-live-trade');
  if (ot) {
    const entry = ot.entry_price || 0;
    const cur = price || entry;
    const livePnl = entry ? (cur - entry) / entry : 0;
    const pnlColor = livePnl >= 0 ? '#22c55e' : '#ef4444';
    ovLive.innerHTML = `<div class="live-trade">
      <div class="live-header"><div class="live-pulse"></div><span class="live-pill">Live BTC Trade Open</span><span style="color:#475569;font-size:0.75rem">since ${fmtTs(ot.entry_ts)}</span></div>
      <div class="live-body">
        <div class="live-item"><div class="lbl">Entry</div><div class="val">${fmt(entry)}</div></div>
        <div class="live-item"><div class="lbl">Current</div><div class="val">${fmt(cur)}</div></div>
        <div class="live-item"><div class="lbl">Live PnL</div><div class="val" style="color:${pnlColor}">${fmtPct(livePnl)}</div></div>
        <div class="live-item"><div class="lbl">Strategy</div><div class="val">v${ot.strategy_version || '?'}</div></div>
      </div>
    </div>`;
  } else {
    ovLive.innerHTML = '';
  }

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
    // Parse threshold from strategy YAML
    let threshold = 35, stopLoss = 1.0, exitThreshold = 55, tf = '15m';
    if (status.strategy) {
      const thMatch = status.strategy.match(/threshold:\\s*(\\d+)/);
      const slMatch = status.strategy.match(/stop_loss_pct:\\s*([\\d.]+)/);
      const exMatch = status.strategy.match(/exit_rsi_threshold:\\s*(\\d+)/);
      const tfMatch = status.strategy.match(/timeframe:\\s*(\\S+)/);
      if (thMatch) threshold = thMatch[1];
      if (slMatch) stopLoss = slMatch[1];
      if (exMatch) exitThreshold = exMatch[1];
      if (tfMatch) tf = tfMatch[1];
    }
    const emptyEl = document.getElementById('empty-state');
    if (emptyEl) emptyEl.innerHTML = `<strong>No closed trades yet</strong>Waiting for ${tf} RSI &lt; ${threshold} entry · take-profit RSI &gt; ${exitThreshold} · stop loss ${stopLoss}%`;
    tableDiv.innerHTML = `<div class="empty" id="empty-state"><strong>No closed trades yet</strong>Waiting for ${tf} RSI &lt; ${threshold} entry · take-profit RSI &gt; ${exitThreshold} · stop loss ${stopLoss}%</div>`;
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

    // Also update BTC logs tab
    const btcLogsEl = document.getElementById('btc-logs');
    if (btcLogsEl) btcLogsEl.innerHTML = `<div class="log-entry">
      <div class="log-header">
        <span class="badge asset-btc">BTC</span>
        <span style="font-weight:700">v${hyp.version || '?'}</span>
        <span style="color:#475569;font-size:0.75rem">${hyp.mode || '—'} mode</span>
        <span style="color:#64748b;font-size:0.72rem;margin-left:auto">${fmtTs(hyp.ts)}</span>
      </div>
      <div style="font-size:0.75rem;color:#64748b;margin-bottom:4px">Changed: ${hyp.changed || '—'} · Score before: ${hyp.score_before != null ? hyp.score_before.toFixed(3) : '—'}</div>
      <div class="log-reasoning">${hyp.rationale || '—'}</div>
    </div>`;
  } else {
    refDiv.innerHTML = '<div class="empty">No reflections yet — fires after 25 closed trades (batch review).</div>';
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

// ── Tab navigation ──────────────────────────────────────────
function showTab(name, el) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const pane = document.getElementById('tab-' + name);
  if (pane) pane.classList.add('active');
  if (el) el.classList.add('active');
}

// ── Stock watchlist ──────────────────────────────────────────
let stockData = [];

async function fetchStocks() {
  try {
    stockData = await fetch('/stocks/watchlist').then(r => r.json());
    renderStocks();
    renderOverviewStocks();
    renderActiveTrades();
    renderAllTrades();
  } catch(e) { console.error('stock fetch failed', e); }
}

async function fetchStockLogs() {
  try {
    const logs = await fetch('/stocks/logs').then(r => r.json());
    renderStockLogs(logs);
  } catch(e) {}
}

function sigClass(signal) {
  if (signal === 'entry_confirmed') return 'sig sig-entry';
  if (signal === 'watching' || signal === 'watching_possible_wave_2' || signal === 'watching_possible_wave_4') return 'sig sig-watch';
  if (signal === 'waiting_for_retracement') return 'sig sig-wait';
  if (signal === 'invalidated_setup') return 'sig sig-invalid';
  return 'sig sig-none';
}

function sigLabel(signal) {
  const map = {
    entry_confirmed: 'Entry',
    watching: 'Watching',
    waiting_for_retracement: 'Waiting',
    watching_possible_wave_2: 'Wave 2?',
    watching_possible_wave_4: 'Wave 4?',
    invalidated_setup: 'Invalidated',
    trend_unclear: 'Unclear',
    no_valid_setup: 'No Setup',
  };
  return map[signal] || signal;
}

function renderStocks() {
  const el = document.getElementById('stock-list');
  if (!stockData.length) { el.innerHTML = '<div class="empty"><strong>No stocks yet</strong>Add a ticker above.</div>'; return; }

  el.innerHTML = stockData.map(s => {
    const inTrade = s.position_status === 'in_trade';
    const rowClass = inTrade ? 'stock-row in-trade' : s.trading_enabled ? 'stock-row trading-on' : 'stock-row';
    const changeColor = (s.daily_change_pct || 0) >= 0 ? '#22c55e' : '#ef4444';
    const changeStr = s.daily_change_pct != null ? `${s.daily_change_pct >= 0 ? '+' : ''}${s.daily_change_pct.toFixed(2)}%` : '—';
    const toggleClass = s.trading_enabled ? 'toggle-btn on' : 'toggle-btn';
    const toggleLabel = s.trading_enabled ? '● Trading On' : '○ Trading Off';

    return `<div class="${rowClass}">
      <div class="stock-top">
        <span class="stock-ticker">${s.ticker}</span>
        <span class="stock-name">${s.company_name || ''}</span>
        <span class="${sigClass(s.signal)}">${sigLabel(s.signal)}</span>
        <button class="${toggleClass}" onclick="toggleStock('${s.ticker}', ${!s.trading_enabled})">${toggleLabel}</button>
        <button onclick="removeStock('${s.ticker}')" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.78rem;margin-left:auto">✕ Remove</button>
        <span class="stock-price">${s.current_price != null ? '$' + s.current_price.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}) : '—'}</span>
        <span class="stock-change" style="color:${changeColor}">${changeStr}</span>
      </div>
      <div class="stock-bottom">
        <div class="stock-field"><div class="lbl">Trend</div><div class="val" style="color:${s.trend==='bullish'?'#22c55e':s.trend==='bearish'?'#ef4444':'#94a3b8'}">${s.trend || '—'}</div></div>
        <div class="stock-field"><div class="lbl">Wave Count</div><div class="val">${s.wave_count || '—'}</div></div>
        <div class="stock-field"><div class="lbl">Fib Zone</div><div class="val">${s.fib_zone || '—'}</div></div>
        <div class="stock-field"><div class="lbl">Confidence</div><div class="val" style="color:${(s.confidence_score||0)>=65?'#22c55e':(s.confidence_score||0)>=40?'#f59e0b':'#ef4444'}">${s.confidence_score || 0}/100</div></div>
        <div class="stock-field"><div class="lbl">Position</div><div class="val">${s.position_status || 'watching'}</div></div>
        <div class="stock-field"><div class="lbl">Entry</div><div class="val">${s.entry_price ? '$'+s.entry_price.toFixed(2) : '—'}</div></div>
        <div class="stock-field"><div class="lbl">Stop Loss</div><div class="val pnl-negative">${s.stop_loss_price ? '$'+s.stop_loss_price.toFixed(2) : '—'}</div></div>
        <div class="stock-field"><div class="lbl">Target</div><div class="val pnl-positive">${s.take_profit_price ? '$'+s.take_profit_price.toFixed(2) : '—'}</div></div>
        <div class="stock-field"><div class="lbl">Risk/Reward</div><div class="val">${s.risk_reward || '—'}</div></div>
        <div class="stock-field"><div class="lbl">Risk %</div><div class="val">${s.risk_pct || 1.5}%</div></div>
      </div>
      ${s.hermes_notes ? `<div class="stock-notes">🤖 ${s.hermes_notes}</div>` : ''}
    </div>`;
  }).join('');
}

async function addStock() {
  const ticker = document.getElementById('new-ticker').value.trim().toUpperCase();
  const name = document.getElementById('new-name').value.trim();
  if (!ticker) return;
  await fetch('/stocks/watchlist', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ticker, company_name: name})});
  document.getElementById('new-ticker').value = '';
  document.getElementById('new-name').value = '';
  fetchStocks();
}

async function removeStock(ticker) {
  if (!confirm(`Remove ${ticker} from watchlist?`)) return;
  await fetch('/stocks/watchlist/' + ticker, {method:'DELETE'});
  fetchStocks();
}

async function toggleStock(ticker, enabled) {
  await fetch('/stocks/watchlist/' + ticker + '/toggle', {method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({enabled})});
  fetchStocks();
}

function renderOverviewStocks() {
  const watching = stockData.length;
  const enabled = stockData.filter(s => s.trading_enabled).length;
  const inTrade = stockData.filter(s => s.position_status === 'in_trade').length;
  document.getElementById('ov-watching').textContent = watching;
  document.getElementById('ov-enabled').textContent = enabled;
  document.getElementById('ov-in-trade').textContent = inTrade;
  document.getElementById('stock-status-label').textContent = `${watching} tickers · ${enabled} active`;
}

function renderActiveTrades() {
  const el = document.getElementById('active-trades-body');
  const activeStocks = stockData.filter(s => s.position_status === 'in_trade');
  const btcTrade = statusData?.open_trade;

  if (!btcTrade && !activeStocks.length) {
    el.innerHTML = '<div class="empty">No active positions.</div>';
    document.getElementById('active-meta').textContent = '0 positions';
    return;
  }

  let html = '';
  if (btcTrade) {
    const entry = btcTrade.entry_price || 0;
    const cur = statusData.last_price || entry;
    const pnl = entry ? (cur - entry) / entry : 0;
    const pnlColor = pnl >= 0 ? '#22c55e' : '#ef4444';
    html += `<div class="log-entry" style="border-color:#f59e0b44">
      <div class="log-header">
        <span class="badge asset-btc">BTC</span>
        <span style="font-weight:700">BTC/USDT LONG</span>
        <span style="color:#475569;font-size:0.75rem">${fmtTs(btcTrade.entry_ts)}</span>
        <span style="color:${pnlColor};font-weight:700;margin-left:auto">${fmtPct(pnl)} live</span>
      </div>
      <div style="font-size:0.8rem;color:#94a3b8">Entry: ${fmt(entry)} · Current: ${fmt(cur)} · Stop: ${fmt(entry*(1-0.01))}</div>
    </div>`;
  }

  activeStocks.forEach(s => {
    const pnl = s.entry_price && s.current_price ? (s.current_price - s.entry_price) / s.entry_price : null;
    const pnlColor = (pnl || 0) >= 0 ? '#22c55e' : '#ef4444';
    html += `<div class="log-entry" style="border-color:#0AAAFF44">
      <div class="log-header">
        <span class="badge asset-stock">STOCK</span>
        <span style="font-weight:700">${s.ticker} LONG</span>
        <span style="color:#475569;font-size:0.75rem">${s.company_name}</span>
        <span style="color:${pnlColor};font-weight:700;margin-left:auto">${pnl != null ? fmtPct(pnl) + ' live' : '—'}</span>
      </div>
      <div style="font-size:0.8rem;color:#94a3b8">Entry: ${fmt(s.entry_price)} · Current: ${fmt(s.current_price)} · Stop: ${fmt(s.stop_loss_price)} · Target: ${fmt(s.take_profit_price)}</div>
      ${s.hermes_notes ? `<div style="font-size:0.75rem;color:#64748b;margin-top:4px;font-style:italic">${s.hermes_notes}</div>` : ''}
    </div>`;
  });

  el.innerHTML = html;
  document.getElementById('active-meta').textContent = `${(btcTrade ? 1 : 0) + activeStocks.length} position(s)`;
}

async function renderAllTrades() {
  const el = document.getElementById('all-trades-table');
  try {
    const [btcTrades, stockTrades] = await Promise.all([
      fetch('/trades').then(r => r.json()),
      fetch('/stocks/trades').then(r => r.json()),
    ]);
    const combined = [
      ...btcTrades.map(t => ({...t, asset_type: 'btc'})),
      ...stockTrades.map(t => ({...t})),
    ].sort((a, b) => (b.exit_ts || '').localeCompare(a.exit_ts || '')).slice(0, 50);

    if (!combined.length) { el.innerHTML = '<div class="empty">No closed trades yet.</div>'; return; }

    const rows = combined.map(t => {
      const pnl = t.pnl_pct;
      const pnlClass = (pnl || 0) > 0 ? 'pnl-positive' : (pnl || 0) < 0 ? 'pnl-negative' : 'pnl-neutral';
      const assetBadge = t.asset_type === 'btc'
        ? `<span class="badge asset-btc">BTC</span>`
        : `<span class="badge asset-stock">STOCK</span>`;
      return `<tr>
        <td>${assetBadge}</td>
        <td style="font-weight:700">${t.ticker || t.asset || '—'}</td>
        <td>${fmtTs(t.entry_ts)}</td>
        <td>${fmt(t.entry_price)}</td>
        <td>${fmt(t.exit_price)}</td>
        <td><span class="${pnlClass}">${fmtPct(pnl)}</span></td>
        <td style="color:#64748b;font-size:0.75rem">${t.exit_reason || '—'}</td>
      </tr>`;
    }).join('');
    el.innerHTML = `<table><thead><tr><th>Type</th><th>Asset</th><th>Entry Time</th><th>Entry $</th><th>Exit $</th><th>PnL</th><th>Reason</th></tr></thead><tbody>${rows}</tbody></table>`;
  } catch(e) { el.innerHTML = '<div class="empty">Could not load trades.</div>'; }
}

function renderStockLogs(logs) {
  const el = document.getElementById('stock-logs');
  if (!logs.length) { el.innerHTML = '<div class="empty">No stock logs yet.</div>'; return; }
  el.innerHTML = [...logs].reverse().slice(0, 20).map(l => `
    <div class="log-entry">
      <div class="log-header">
        <span class="badge asset-stock">STOCK</span>
        <span style="font-weight:700">${l.symbol}</span>
        <span class="${sigClass(l.signal)}">${sigLabel(l.signal)}</span>
        <span style="color:${(l.confidence||0)>=65?'#22c55e':'#f59e0b'};font-size:0.75rem">${l.confidence||0}/100</span>
        <span style="color:#334155;font-size:0.72rem;margin-left:auto">${fmtTs(l.ts)}</span>
      </div>
      <div style="font-size:0.75rem;color:#64748b;margin-bottom:4px">Wave: ${l.wave_count||'—'} · Fib: ${l.fib_zone||'—'} · Trend: ${l.trend||'—'} · R/R: ${l.risk_reward||'—'}</div>
      <div class="log-reasoning">${l.reasoning || '—'}</div>
    </div>`).join('');
}

// ── Strategy selector ────────────────────────────────────────
let strategyData = [];
let perfData = {};

async function fetchStrategies() {
  try {
    const [strategies, perf, phase] = await Promise.all([
      fetch('/strategy/list').then(r => r.json()),
      fetch('/strategy/performance').then(r => r.json()),
      fetch('/strategy/phase').then(r => r.json()),
    ]);
    strategyData = strategies;
    perfData = perf;
    renderStrategies();
    renderPerformanceTable();
    renderPhase(phase);
  } catch(e) { console.error('strategy fetch failed', e); }
}

function renderPhase(p) {
  const label = document.getElementById('phase-label');
  const body = document.getElementById('phase-body');
  if (!p || !label || !body) return;

  label.textContent = `Phase ${p.current_phase}: ${p.phase_name}`;

  const checks = p.checks || {};
  const checkRows = Object.values(checks).map(c => {
    const icon = c.passed ? '✓' : '✗';
    const color = c.passed ? '#22c55e' : '#ef4444';
    return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #0f172a">
      <span style="color:${color};font-weight:800;font-size:1rem;flex-shrink:0">${icon}</span>
      <span style="font-size:0.82rem;flex:1">${c.label}</span>
      <span style="font-size:0.78rem;color:${c.passed?'#22c55e':'#94a3b8'};flex-shrink:0">${c.value} / ${c.target}</span>
    </div>`;
  }).join('');

  // Progress bar
  const pct = p.overall_progress_pct || 0;
  const barColor = p.phase_passed ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#0AAAFF';

  // Trade progress bar
  const tradePct = checks.trades_progress?.progress_pct || 0;

  body.innerHTML = `
    <div style="margin-bottom:12px">
      <div style="font-size:0.78rem;color:#64748b;margin-bottom:6px">${p.phase_description}</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-size:0.72rem;color:#475569">Conditions met</span>
        <span style="font-size:0.72rem;font-weight:700;color:${barColor}">${p.passed_count}/${p.total_checks}</span>
      </div>
      <div style="background:#1e293b;border-radius:4px;height:6px;overflow:hidden">
        <div style="height:100%;background:${barColor};border-radius:4px;width:${pct}%;transition:width 0.5s"></div>
      </div>
    </div>
    ${tradePct < 100 ? `<div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-size:0.72rem;color:#475569">Trade count progress</span>
        <span style="font-size:0.72rem;font-weight:700;color:#0AAAFF">${checks.trades_progress?.value||0}/${checks.trades_progress?.target||100}</span>
      </div>
      <div style="background:#1e293b;border-radius:4px;height:4px;overflow:hidden">
        <div style="height:100%;background:#0AAAFF;border-radius:4px;width:${tradePct}%;transition:width 0.5s"></div>
      </div>
    </div>` : ''}
    <div>${checkRows}</div>
    <div style="margin-top:12px;padding:10px;background:${p.phase_passed?'#22c55e11':'#0f172a'};border-radius:8px;border:1px solid ${p.phase_passed?'#22c55e44':'#1e293b'}">
      <div style="font-size:0.8rem;color:${p.phase_passed?'#22c55e':'#94a3b8'};line-height:1.5">${p.verdict}</div>
      ${p.unlock_next && p.phase_passed ? `<div style="font-size:0.75rem;color:#475569;margin-top:4px">Next: ${p.unlock_next}</div>` : ''}
    </div>`;
}

function renderStrategies() {
  const el = document.getElementById('strategy-list');
  const activeLabel = document.getElementById('strat-active-label');
  const active = strategyData.find(s => s.active);
  if (activeLabel && active) activeLabel.textContent = `Active: ${active.name}`;

  if (!strategyData.length) {
    el.innerHTML = '<div class="empty">No strategies registered yet. Run at least one trade to bootstrap.</div>';
    return;
  }

  el.innerHTML = strategyData.map(s => {
    const perf = s.performance || {};
    const isActive = s.active;
    const isLocked = s.locked;
    const expectancy = perf.expectancy_pct != null ? perf.expectancy_pct : null;
    const hasEdge = expectancy > 0 && (perf.total_trades || 0) >= 25;
    const borderColor = isActive ? '#0AAAFF' : isLocked ? '#22c55e' : '#1e293b';

    return `<div style="background:#111827;border:1px solid ${borderColor};border-radius:12px;padding:14px 16px;margin-bottom:10px">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
        <span style="font-size:1rem;font-weight:800;color:#f8fafc">${s.name}</span>
        ${isActive ? '<span class="badge asset-stock">ACTIVE</span>' : ''}
        ${isLocked ? '<span class="badge" style="background:#22c55e22;color:#22c55e;border:1px solid #22c55e33">🔒 LOCKED</span>' : ''}
        ${hasEdge ? '<span class="badge" style="background:#22c55e22;color:#22c55e;border:1px solid #22c55e33">✓ Edge Detected</span>' : ''}
        <span style="color:#475569;font-size:0.75rem;margin-left:auto">${fmtTs(s.created_at)}</span>
      </div>
      ${s.description ? `<div style="font-size:0.78rem;color:#64748b;margin-bottom:8px">${s.description}</div>` : ''}
      ${s.reason_created ? `<div style="font-size:0.78rem;color:#475569;margin-bottom:8px;font-style:italic">Created because: ${s.reason_created}</div>` : ''}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:8px;margin-bottom:10px">
        <div><div style="font-size:0.62rem;color:#475569;text-transform:uppercase;margin-bottom:2px">Trades</div><div style="font-size:0.85rem;font-weight:700">${perf.total_trades || 0}</div></div>
        <div><div style="font-size:0.62rem;color:#475569;text-transform:uppercase;margin-bottom:2px">Win Rate</div><div style="font-size:0.85rem;font-weight:700;color:${(perf.win_rate_pct||0)>=50?'#22c55e':'#ef4444'}">${perf.win_rate_pct != null ? perf.win_rate_pct+'%' : '—'}</div></div>
        <div><div style="font-size:0.62rem;color:#475569;text-transform:uppercase;margin-bottom:2px">Expectancy</div><div style="font-size:0.85rem;font-weight:700;color:${expectancy>0?'#22c55e':expectancy<0?'#ef4444':'#94a3b8'}">${expectancy != null ? (expectancy>=0?'+':'')+expectancy.toFixed(4)+'%' : '—'}</div></div>
        <div><div style="font-size:0.62rem;color:#475569;text-transform:uppercase;margin-bottom:2px">Profit Factor</div><div style="font-size:0.85rem;font-weight:700;color:${(perf.profit_factor||0)>=1?'#22c55e':'#ef4444'}">${perf.profit_factor != null ? perf.profit_factor : '—'}</div></div>
        <div><div style="font-size:0.62rem;color:#475569;text-transform:uppercase;margin-bottom:2px">Max DD</div><div style="font-size:0.85rem;font-weight:700;color:${(perf.max_drawdown_pct||0)>8?'#ef4444':'#94a3b8'}">${perf.max_drawdown_pct != null ? perf.max_drawdown_pct+'%' : '—'}</div></div>
        <div><div style="font-size:0.62rem;color:#475569;text-transform:uppercase;margin-bottom:2px">Quality</div><div style="font-size:0.85rem;font-weight:700;color:${perf.data_quality==='reliable'?'#22c55e':perf.data_quality==='useful'?'#f59e0b':'#64748b'}">${perf.data_quality || '—'}</div></div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        ${!isActive ? `<button onclick="selectStrategy('${s.name}')" style="background:#0AAAFF;color:#080f1a;border:none;padding:6px 14px;border-radius:8px;font-weight:700;font-size:0.78rem;cursor:pointer">Set Active</button>` : ''}
        ${!isLocked ? `<button onclick="lockStrategy('${s.name}')" style="background:#22c55e22;color:#22c55e;border:1px solid #22c55e44;padding:6px 14px;border-radius:8px;font-weight:700;font-size:0.78rem;cursor:pointer">🔒 Lock</button>` : `<button onclick="unlockStrategy('${s.name}')" style="background:#ef444422;color:#ef4444;border:1px solid #ef444444;padding:6px 14px;border-radius:8px;font-weight:700;font-size:0.78rem;cursor:pointer">Unlock</button>`}
      </div>
    </div>`;
  }).join('');
}

function renderPerformanceTable() {
  const el = document.getElementById('perf-table');
  const entries = Object.entries(perfData);
  if (!entries.length) {
    el.innerHTML = '<div class="empty">No trades yet. Performance data will appear after first trades.</div>';
    return;
  }
  const rows = entries.map(([name, p]) => {
    const edgeColor = p.expectancy_pct > 0 ? '#22c55e' : '#ef4444';
    return `<tr>
      <td style="font-weight:700">${name}</td>
      <td>${p.total_trades}</td>
      <td style="color:${p.win_rate_pct>=50?'#22c55e':'#ef4444'}">${p.win_rate_pct}%</td>
      <td style="color:#22c55e">+${p.avg_win_pct}%</td>
      <td style="color:#ef4444">-${p.avg_loss_pct}%</td>
      <td style="color:${p.profit_factor>=1?'#22c55e':'#ef4444'}">${p.profit_factor}x</td>
      <td style="color:${edgeColor};font-weight:700">${p.expectancy_pct>=0?'+':''}${p.expectancy_pct}%</td>
      <td style="color:${p.max_drawdown_pct>8?'#ef4444':'#94a3b8'}">${p.max_drawdown_pct}%</td>
      <td style="color:${p.data_quality==='reliable'?'#22c55e':p.data_quality==='useful'?'#f59e0b':'#64748b'}">${p.data_quality}</td>
    </tr>`;
  }).join('');
  el.innerHTML = `<div class="table-wrap"><table>
    <thead><tr><th>Strategy</th><th>Trades</th><th>Win%</th><th>Avg Win</th><th>Avg Loss</th><th>PF</th><th>Expectancy</th><th>Max DD</th><th>Quality</th></tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;
}

async function selectStrategy(name) {
  await fetch('/strategy/select/' + name, {method:'POST'});
  fetchStrategies();
}

async function lockStrategy(name) {
  if (!confirm(`Lock strategy ${name}? Claude cannot modify it until you unlock it.`)) return;
  await fetch('/strategy/lock/' + name, {method:'POST'});
  fetchStrategies();
}

async function unlockStrategy(name) {
  await fetch('/strategy/unlock/' + name, {method:'POST'});
  fetchStrategies();
}

// ── Main fetch ──────────────────────────────────────────────
async function fetchAll() {
  const [status, trades] = await Promise.all([
    fetch('/status').then(r => r.json()),
    fetch('/trades').then(r => r.json())
  ]);
  statusData = status;
  allTrades = trades;
  render(status, trades);
}

async function fetchAllData() {
  await Promise.all([fetchAll(), fetchStocks(), fetchStockLogs(), fetchStrategies()]);
}

// Refresh every 5s
fetchAllData();
setInterval(fetchAllData, 5000);
</script>
</body>
</html>"""


_DASHBOARD_HTML = _build_dashboard_html()


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
