# Nexus

> A self-built personal command center — autonomous trading, banking, mobile, and schedule automation.

![Trading Bot](https://img.shields.io/badge/Hermes-live-22c55e?style=flat-square)
![Banking API](https://img.shields.io/badge/Nexus%20API-live-22c55e?style=flat-square)

---

## What is Nexus?

Nexus is a personal ecosystem of interconnected tools I built to manage trading, finances, work schedule, and daily life from one place. Every component is production-deployed and actively running.

---

## Projects

### 🤖 [`trading-bot/`](./trading-bot) — Hermes Trading Bot
**Autonomous paper trading agent running 24/7 on Railway.**

- **Strategy:** Elliott Wave + Fibonacci retracement analysis on 30 stocks and BTC/USD (Kraken)
- **Setup types:** `retracement_entry` (price in 38.2–61.8% fib zone), `breakout_continuation` (price above swing high)
- **Risk firewall:** Hardcoded safety limits that cannot be modified by AI — min R/R, confidence, stop size, position limits
- **AI layer:** Claude Haiku writes natural-language analysis per stock scan; Claude Sonnet reflects on strategy in batches
- **Analytics:** Rejection reason tracking, setup-type performance, expectancy calculation, phase gate system
- **Dashboard:** 8-tab real-time web UI with Hermes Analysis Chart (custom fib overlays), TradingView integration, trade idea browser
- **Persistence:** Supabase Postgres as canonical source of truth — survives container restarts
- **Goal:** 100 paper trades → prove positive expectancy → advance to live trading

**Live:** [private]

---

### 📱 [`android/`](./android) — Nexus Android App
**Personal command-center Android app.**

- Calendar with push notification reminders
- Work shift tracking for two jobs (Pebble Creek + Best Buy) with auto-sync via Work Schedule Sync
- Budget tracking with expense categories and credit card progress bars
- Banking tab → live bank/investment data via Nexus API (Plaid)
- Trading tab → live BTC paper trades, PnL, and strategy status from Hermes
- Built with Kotlin + Jetpack Compose + Room + Material 3

---

### 🏦 [`api/`](./api) — Nexus API
**Personal backend for banking and investment data.**

- Plaid integration: bank account linking, live balances, transaction history, Fidelity holdings
- Stores Plaid access tokens in Supabase (server-side — no credentials on device)
- Web banking dashboard at the live URL
- Intentionally thin service — clean API surface over Plaid SDK

**Live:** [private]

---

### 📅 [`schedule-sync/`](./schedule-sync) — Work Schedule Sync
**Google Apps Script that syncs two work schedules into Google Calendar automatically.**

- **Pebble Creek:** Reads shared calendar feed, auto-detects shift type from event title
- **Best Buy:** Claude Haiku OCR reads schedule screenshots from Google Drive — drop a screenshot, it processes automatically
- Deduplication via `PropertiesService` — never parses the same file twice
- Email summary after each sync run

---

## Architecture

```
Nexus Ecosystem
│
├── hermes-trading    (Railway)   ← BTC + stock trading, web dashboard
├── dashboard-api     (Railway)   ← Plaid banking backend
├── dashboard-app     (Android)   ← Mobile command center
└── work-schedule-sync (Apps Script) ← Calendar automation
         │
         └── All services talk through REST APIs
             Data persisted in Supabase Postgres
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Trading bot | Python · FastAPI · ccxt (Kraken) · yfinance · asyncpg |
| AI | Anthropic SDK — Claude Haiku (analysis) · Claude Sonnet (reflection) |
| Charts | TradingView Lightweight Charts + TradingView embed |
| Android | Kotlin · Jetpack Compose · Room · Retrofit · WorkManager |
| API backend | Python · FastAPI · Plaid SDK |
| Database | Supabase Postgres |
| Deployment | Railway (auto-deploy on push) |
| Automation | Google Apps Script |

---

## Brand

| | |
|---|---|
| Name | Nexus |
| Tagline | Your personal command center |
| Primary | `#0AAAFF` (Nexus Blue) |
| Background | `#080F1A` |
| Accent | `#8B5CF6` (Nexus Purple) |
| Success | `#22C55E` |

---

*Personal project — not licensed for redistribution.*
