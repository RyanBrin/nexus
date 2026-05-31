# Nexus

> Your personal command center.

A self-built personal dashboard ecosystem — trading bot, finance dashboard, Android app, and schedule sync. Everything connected in one place.

---

## Projects

### 📱 [`android/`](./android) — Nexus Android App
Personal dashboard app for tracking everything in one place.
- Calendar, shifts, budget with spending caps, stocks, bank accounts
- **Hermes Trading** screen — live BTC paper trading bot data
- Bank integration via Plaid (balances, transactions, Fidelity brokerage)
- Push notifications for events and shifts
- Built with Kotlin + Jetpack Compose + Room + Material 3

### 🤖 [`trading-bot/`](./trading-bot) — Hermes Trading Bot
Self-improving BTC/USDT paper trading agent running 24/7 on Railway.
- RSI-based entry signals + TradingView webhook support
- Logs every trade to Supabase
- After every 5 closed trades, calls Claude AI to reflect and evolve the strategy
- Live dashboard at [hermes-trading-production-c312.up.railway.app](https://hermes-trading-production-c312.up.railway.app)
- Built with Python + FastAPI + ccxt + Anthropic SDK

### 🏦 [`api/`](./api) — Dashboard API
Personal backend API handling bank and investment data.
- Plaid integration for real bank account connections
- Endpoints: accounts, transactions, investments (Fidelity holdings)
- Live at [dashboard-api-production-ebee.up.railway.app](https://dashboard-api-production-ebee.up.railway.app)
- Built with Python + FastAPI + Supabase

### 📅 [`schedule-sync/`](./schedule-sync) — Work Schedule Sync
Google Apps Script that auto-syncs work schedules to Google Calendar.
- Pebble Creek Golf Course shifts (opening/closing/float detection)
- Best Buy shifts parsed from screenshots via Claude AI + OCR
- Processes only new files, skips already-handled screenshots

---

## Tech Stack

| Layer | Tech |
|---|---|
| Android | Kotlin, Jetpack Compose, Room, Retrofit, WorkManager |
| Trading Bot | Python, FastAPI, ccxt (Kraken), Anthropic API |
| API Backend | Python, FastAPI, Plaid SDK, asyncpg |
| Database | Supabase (Postgres) |
| Infra | Railway (auto-deploy from GitHub) |
| AI | Claude claude-sonnet-4-6 (reflections), Claude Haiku (schedule parsing) |

---

## Architecture

```
nexus/
├── android/          # Kotlin Android app
├── trading-bot/      # Python trading agent (Railway)
├── api/              # Python personal API (Railway)
└── schedule-sync/    # Google Apps Script
```

Both backend services deploy automatically to Railway on every push to `main`.

---

*Personal project — not licensed for redistribution.*
