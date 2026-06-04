# Hermes Trading Bot

> Self-improving BTC paper trading agent + stock swing-trade analyzer.

Part of the **[Nexus](https://github.com/RyanBrin/nexus)** ecosystem — canonical source at `nexus/trading-bot/`.

---

## What it does

**BTC Bot**
- Trades BTC/USDT paper positions using 15-minute RSI signals
- Entry: RSI < 35 (oversold) | Take-profit: RSI > 55 | Stop loss: 1%
- Every trade gets a full reason report logged
- Reflects and evolves strategy every 25 trades (batch review, not after each trade)
- Locked strategies cannot be changed by the AI

**Stock Analyzer**
- Scans manually selected watchlist (AAPL, NVDA, TSLA, AMD, MSFT + custom tickers)
- Elliott Wave + Fibonacci retracement analysis per ticker
- Per-ticker news sentiment (NewsAPI)
- Risk Manager with hardcoded guardrails (cannot be auto-modified)
- Every setup logged as a trade idea with full reasoning + rejection reason if blocked

**Strategy System**
- Named, versioned strategies (v01, v02, ...)
- Locked strategies survive forever — nothing gets overwritten
- Performance per strategy: win rate, expectancy, profit factor, max drawdown
- Phase gate: must hit 100 paper trades + positive expectancy before advancing

---

## Architecture

```
hermes_trading/
  loop.py              ← BTC trading loop (60s ticks)
  stocks/loop.py       ← Stock scan loop (5min ticks)
  agents/
    risk_manager.py    ← Hard veto — NEVER auto-modified
    evaluator.py       ← Setup scorer (Elliott Wave + news)
    news_agent.py      ← Per-ticker news sentiment
  strategy_registry.py ← Named/versioned/lockable strategies
  performance.py       ← Expectancy, profit factor, win rate
  phase_tracker.py     ← Phase 1/2/3 pass conditions
  reflect.py           ← Batch reflection (25 trades minimum)
  trade_ideas.py       ← Every setup logged with reasoning
  agent_state.py       ← Hermes status + configurable settings
  server.py            ← FastAPI dashboard (6 tabs)
```

## Dashboard tabs
- **Overview** — BTC + stocks summary, phase progress
- **BTC Bot** — live trade, cumulative PnL chart, trade history
- **Stocks** — watchlist with Elliott Wave signals, toggles
- **Active Trades** — BTC + stocks combined
- **Strategies** — version selector, lock/unlock, expectancy table
- **⚙ Control Center** — running status, trade ideas, risk rules, settings
- **Logs** — full activity log

## Goal
> Phase 1: Paper trade 100 trades minimum. Pass: positive expectancy, PF > 1.3, max DD < 10%, every trade has stop + reason.

**Live:** [private]

## Tech
Python · FastAPI · ccxt (Kraken) · yfinance · Anthropic SDK · Supabase · Railway