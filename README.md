# Nexus

> Your personal command center.

A self-built personal dashboard ecosystem — trading bot, finance dashboard, Android app, and schedule sync. Everything connected in one place.

---

## Projects

### 📱 [`android/`](./android) — Nexus Android App
Personal dashboard app for tracking everything in one place.
- Calendar, work shifts (Pebble Creek + Best Buy), budget with editable spending caps + donut chart
- **Trading screen** — live BTC paper trading data, open trade card, cumulative PnL chart
- Bank integration via Plaid (balances, transactions, Fidelity brokerage holdings)
- Push notifications 1 hour before events and shifts
- Settings screen — API keys stored in EncryptedSharedPreferences
- Built with Kotlin + Jetpack Compose + Room + Material 3

### 🤖 [`trading-bot/`](./trading-bot) — Hermes Trading Bot
Self-improving BTC/USDT paper trading agent running 24/7 on Railway.
- **Strategy:** 15-minute RSI — enter LONG when RSI < 35, take profit when RSI > 55, stop loss at 1%
- TradingView webhook support for external signals
- Every trade logged to Supabase — survives container restarts
- After every 5 closed trades, Claude AI reflects and evolves exactly one strategy variable
- **Goal:** +5%/month (+60%/year) with max 8% drawdown
- Live dashboard: [hermes-trading-production-c312.up.railway.app](https://hermes-trading-production-c312.up.railway.app)
- Built with Python + FastAPI + ccxt (Kraken) + Anthropic SDK

### 🏦 [`api/`](./api) — Dashboard API
Personal backend API handling bank and investment data.
- Plaid integration — live balances, transaction history (30 days), Fidelity brokerage holdings
- Web dashboard: [dashboard-api-production-ebee.up.railway.app](https://dashboard-api-production-ebee.up.railway.app)
- Built with Python + FastAPI + Plaid SDK + Supabase

### 📅 [`schedule-sync/`](./schedule-sync) — Work Schedule Sync
Google Apps Script that auto-syncs work schedules to Google Calendar.
- Pebble Creek Golf Course: auto-detects closing (2:30–9:30pm), opening (6:30am–2:30pm), float (10am–6pm) shifts
- Best Buy: parses schedule screenshots via Claude Haiku OCR — handles any format automatically
- Tracks processed files so screenshots are never parsed twice
- API key stored in Apps Script Script Properties (never in code)

---

## Brand

| | |
|---|---|
| Name | Nexus |
| Tagline | Your personal command center |
| Primary | `#0AAAFF` |
| Background | `#080F1A` |
| Accent | `#8B5CF6` |

---

## Tech Stack

| Layer | Tech |
|---|---|
| Android | Kotlin, Jetpack Compose, Room, Retrofit, WorkManager, Plaid Link SDK |
| Trading Bot | Python, FastAPI, ccxt (Kraken), asyncpg, Anthropic SDK |
| API Backend | Python, FastAPI, Plaid SDK, asyncpg |
| Database | Supabase (Postgres) — trades, heartbeat, hypotheses, Plaid tokens |
| Infra | Railway (auto-deploy on push to GitHub) |
| AI | Claude claude-sonnet-4-6 (strategy reflection), Claude Haiku (schedule OCR) |

---

## Architecture

```
nexus/
├── android/          # Kotlin Android app (Nexus)
├── trading-bot/      # Python BTC trading agent — Railway
├── api/              # Python personal API — Railway  
└── schedule-sync/    # Google Apps Script
```

Both Railway services auto-deploy on every push to `main` in their individual repos.

---

*Personal project — not licensed for redistribution.*
