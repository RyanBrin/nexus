# Personal Dashboard App

A personal Android dashboard for tracking calendar events, expenses, credit card balances, and a stock watchlist — all stored locally on-device. No accounts, no internet required.

Built with Kotlin + Jetpack Compose.

---

## Screenshots

> _Add screenshots here once the app is running on a device or emulator._

---

## Features (Phase 1 — complete)

| Screen | What it does |
|---|---|
| **Home** | Summary cards: upcoming events, total spending, CC balances, stock portfolio value |
| **Calendar** | Add / edit / delete events with title, date, time, and notes |
| **Budget** | Two tabs — Expenses (by category) and Credit Cards (balance + limit progress bar) |
| **Stocks** | Manual watchlist — ticker, company, price per share, shares owned, total value |

All data is stored in a local Room database. Nothing leaves the device.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Kotlin |
| UI | Jetpack Compose + Material 3 |
| Navigation | Navigation Compose |
| Database | Room (SQLite) |
| Architecture | MVVM — ViewModel + StateFlow + Repository |
| Build | Gradle (Kotlin DSL), AGP 9, KSP |

---

## Project Structure

```
app/src/main/java/com/example/dashboard_app/
├── data/
│   ├── db/          # Room database, DAOs (Event, Transaction, CreditCard, Stock)
│   ├── model/       # Data classes / Room entities
│   └── repository/  # Repositories (EventRepository, BudgetRepository, StockRepository)
├── ui/
│   ├── home/        # HomeScreen
│   ├── calendar/    # CalendarScreen, CalendarViewModel, AddEditEventDialog
│   ├── budget/      # BudgetScreen, BudgetViewModel
│   ├── stocks/      # StocksScreen, StocksViewModel
│   └── theme/       # Color, Type, Theme
├── MainActivity.kt
└── NavGraph.kt      # Bottom nav + NavHost
```

---

## Getting Started

### Requirements

- Android Studio (Ladybug or later)
- Android SDK 36
- JDK bundled with Android Studio (no separate install needed)
- A physical Android device (API 26+) or an emulator (API 26+)

### Build & Run

1. Clone the repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/dashboard-app.git
   ```
2. Open the project root in Android Studio.
3. Let Gradle sync.
4. Run on your device or emulator with the **Run** button (or `Shift+F10`).

> **Note:** The first build takes a few minutes — KSP generates Room boilerplate at compile time.

---

## Roadmap

### Phase 1 — Local MVP ✅
- [x] Room database (Event, Transaction, CreditCard, StockItem)
- [x] HomeScreen with live summary cards
- [x] CalendarScreen — full CRUD
- [x] BudgetScreen — Expenses + Credit Cards tabs
- [x] StocksScreen — manual watchlist
- [x] Bottom navigation
- [x] Material 3 theme (dark/light follows system)
- [x] Input validation on all forms

### Phase 2 — Real Data Integration
- [ ] Live stock prices via [Alpha Vantage](https://www.alphavantage.co) (Retrofit + WorkManager background refresh)
- [ ] Outlook calendar sync via Microsoft Graph API (OAuth2 + MSAL Android SDK)
- [ ] Push notifications for upcoming events (WorkManager)
- [ ] API keys stored securely in `local.properties` / `BuildConfig`
- [ ] OAuth tokens stored in `EncryptedSharedPreferences` (Android Keystore)

### Phase 3 — Cloud, Windows & Advanced Finance
- [ ] Compose Multiplatform — Windows desktop target
- [ ] Optional cloud sync (Firebase or Supabase, end-to-end encrypted)
- [ ] Biometric / PIN lock screen
- [ ] Budgeting charts (spending over time, by category)
- [ ] Export to CSV / PDF
- [ ] CI/CD with GitHub Actions

---

## Security Notes

- No data ever leaves the device in Phase 1.
- API keys (Phase 2) will be stored in `local.properties` (already in `.gitignore`) and accessed via `BuildConfig` — never hardcoded in source.
- OAuth tokens (Phase 2) will be stored in `EncryptedSharedPreferences` backed by the Android Keystore.
- Banking integration is intentionally excluded until a proper security review is done.

---

## License

Personal project — not licensed for redistribution.
