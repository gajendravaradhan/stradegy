# Stradegy

An autonomous, self-improving algorithmic trading system that runs on your own hardware. It researches signals, votes via ensemble strategies, executes through Alpaca, and reports everything through a premium mobile-first PWA — all while continuously learning from its own performance.

**Philosophy:** *Research signals → Ensemble strategy voting → Risk-managed execution → Continuous self-improvement*

📱 **Live App:** https://stradegy.duckdns.org  
📖 **User Journey & Full Documentation:** [USER_JOURNEY.md](./USER_JOURNEY.md)

---

## What It Does

Stradegy is a complete autonomous trading stack designed for a single user. It monitors 209 US equities 24/7, generates trade signals from multiple research sources, votes on them through three distinct algorithmic strategies, and executes trades via Alpaca — all while managing risk and improving itself weekly.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (PWA)                       │
│  Dashboard → Tickers → Alerts → Portfolio → Settings        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │ Research │  │ Ensemble │  │   Risk   │  │   Alpaca   │   │
│  │ Pipeline │→ │ Voting   │→ │  Manager │→ │ Execution  │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘   │
│       │                            │              │         │
│       ▼                            ▼              ▼         │
│  ┌──────────┐              ┌──────────────┐  ┌──────────┐   │
│  │ Discord  │              │ Self-Improve │  │ Backtest │   │
│  │  Alerts  │              │   ment Cycle │  │ Engine   │   │
│  └──────────┘              └──────────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

### Multi-Source Research Pipeline
Scans four independent signal sources and aggregates them into "Gem Signals":

| Source | What It Scans |
|--------|---------------|
| **Reddit** | r/wallstreetbets, r/stocks — public JSON endpoints (no API credentials) |
| **SEC Filings** | Insider transactions and 8-K events |
| **Finnhub News** | Sentiment scoring on financial news |
| **Technical** | RSI, MACD, Bollinger Bands, ADX computed from price data |

Each gem gets a **0–100 score**, classification (Strong / Potential / Watchlist), and per-source breakdown.

### 209-Ticker Universe with Real-Time Data
- Full OHLCV backfill for 209 US equities (20+ years of historical data, ~1M rows)
- Real-time sparkline charts on the Tickers page
- Detailed ticker views with 90-day price history
- Incremental daily updates at 20:00 UTC

### Tiered Discord Alert System
Urgent gems (score ≥85, 3+ sources) → **DM you directly**. Regular gems, trades, and reports → **#general channel**. Risk alerts → **DM only**.

### Three-Strategy Ensemble
| Strategy | Logic |
|----------|-------|
| **Mean Reversion** | Buys oversold using RSI + Bollinger Bands |
| **Momentum Breakout** | Buys breakouts above 20-day highs with volume + ADX |
| **Earnings Momentum** | Buys MACD crossovers with volume confirmation |

The ensemble requires **2 of 3 strategies to agree** before entering a position, reducing false signals.

### Comprehensive Risk Management
- **Position Sizing**: 3% risk per trade, ATR-based stops, 25% max single position
- **Kill Switch**: Trading halts at 20% drawdown from peak
- **PDT Guard**: Monitors 3-day-trade limit for sub-$25k accounts
- **Tax Reserve**: Automatically sets aside 30% of short-term gains
- **Correlation Check**: Warns on over-concentration (>0.8 correlation)

### Self-Improvement Loop
Every Sunday at 02:00 UTC, the bot:
1. Reviews the week's trades
2. Calculates win rate, Sharpe, drawdown
3. Compares live results to backtest expectations
4. Adjusts strategy weights if underperforming
5. Versions improvements or rolls back if degraded

### Walk-Forward Backtesting
Uses rolling windows (train 1 year → test 3 months → roll forward) to validate strategies without peeking at future data.

### Premium PWA Experience
- Mobile-first design with bottom navigation
- Pull-to-refresh gesture support
- App badge for unread alerts
- Offline persistence via TanStack Query cache
- Real-time WebSocket push updates
- Error boundary with graceful fallback UI

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- A free Alpaca paper account ([alpaca.markets](https://alpaca.markets))
- A free Finnhub API key ([finnhub.io](https://finnhub.io))
- (Optional) Discord bot token for alerts

### Installation

```bash
git clone git@github.com:gajendravaradhan/stradegy.git
cd stradegy

# Backend
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate  # or .\backend\.venv\Scripts\activate on Windows
cd backend
pip install -e .
cd ..

# Frontend
cd frontend
npm install
cd ..
```

### Configuration

Create `backend/.env`:

```env
# Required
FINNHUB_API_KEY=your_finnhub_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# Optional — for Discord alerts
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_USER_ID=your_discord_user_id
DISCORD_GENERAL_CHANNEL_ID=your_general_channel_id

# Defaults are safe
PAPER_TRADING=true
AUTONOMY_MODE=semi
```

### Run Locally

```bash
./start.sh
```

This starts:
- **Backend** at `http://localhost:8420`
- **Frontend dev server** at `http://localhost:5173`

The backend auto-seeds 209 tickers into a local SQLite database on first startup.

### Production Deployment

The current deployment uses a Ubuntu VM with native Python execution:

1. **VM Setup**: Python 3.12 venv, Caddy reverse proxy with Let's Encrypt
2. **Auto-start**: systemd service for boot resilience
3. **HTTPS**: Automatic certificate renewal via Caddy
4. **Database**: SQLite with ~1M OHLCV rows for 209 tickers

For detailed deployment instructions, see `plans/DEPLOYMENT.md`.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/health` | System status |
| `GET` | `/api/portfolio` | Real-time Alpaca positions & equity |
| `GET` | `/api/portfolio/metrics` | Portfolio performance metrics |
| `GET` | `/api/alerts` | Hidden gems list |
| `POST` | `/api/alerts/{id}/approve` | Approve and execute a gem alert |
| `POST` | `/api/alerts/{id}/reject` | Reject a gem alert |
| `GET` | `/api/data/tickers` | Full ticker universe with metadata |
| `GET` | `/api/data/tickers/{symbol}` | Ticker detail with 90-day sparkline |
| `GET` | `/api/strategies` | Strategy config & weights |
| `GET` | `/api/settings` | Current settings |
| `POST` | `/api/settings` | Update settings |
| `GET` | `/api/secrets` | Masked secrets configuration |
| `POST` | `/api/backtest/run` | Walk-forward backtest |
| `POST` | `/api/data/backfill` | Backfill historical OHLCV |
| `POST` | `/api/data/incremental` | Incremental data update |
| `WS` | `/api/ws` | Real-time WebSocket updates |

See [USER_JOURNEY.md](./USER_JOURNEY.md) for the complete API reference.

---

## Daily Schedule

| Time (UTC) | What Happens |
|------------|--------------|
| **13:30 (Mon–Fri)** | Market open deep scan for gems |
| **13:45 – 20:00 (Mon–Fri)** | Incremental scan every 15 minutes |
| **20:00 (Mon–Fri)** | Market close scan + data refresh + daily Discord report |
| **02:00 (Sunday)** | Self-improvement cycle + weekly strategy review |
| **1st of month** | Monthly performance report to Discord |
| **1st of quarter** | Quarterly strategy review + mid-term goals |
| **16:00 (Saturday)** | Weekend deep research scan (SEC filings) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), SQLite |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **Data** | Finnhub, Alpaca Markets, SEC EDGAR |
| **Research** | Reddit (public JSON), VADER sentiment, FinBERT, TA-Lib indicators |
| **Execution** | Alpaca REST API |
| **Alerts** | Discord (DM for urgent, channel for routine) |
| **Scheduling** | APScheduler |
| **Reverse Proxy** | Caddy 2 with automatic HTTPS |
| **Testing** | pytest, pytest-asyncio (192 tests) |

---

## Safety Guardrails

| Guardrail | How It Works |
|-----------|--------------|
| **Paper by default** | `PAPER_TRADING=true` in `.env` is the only path to live money |
| **Kill switch** | 20% drawdown from peak halts all trading |
| **PDT guard** | Blocks 4th day trade for sub-$25k accounts |
| **Key distinction** | Alpaca live keys start with `AK`; paper keys start with `PK` |
| **No secrets in git** | `.env` and all credential files are in `.gitignore` |
| **Secrets vault** | Settings page writes to `.env` with `chmod 600` |

---

## Live Trading Graduation

Before switching to live trading, complete the checklist in `plans/LIVE_TRADING_CHECKLIST.md`:

- 4+ weeks of successful paper trading
- Backtest Sharpe ratio > 0.5 and max drawdown < 20%
- Self-improvement cycle has run at least once
- All 192 unit/integration tests passing
- PWA installs on your phone via HTTPS
- Alpaca live account funded with $200 minimum
- `PAPER_TRADING=false` set in `.env`

| Phase | Capital | Strategy |
|-------|---------|----------|
| 1 | $200 | Micro — 1 position, 3% risk |
| 2 | $2,500 | Small — 2–3 positions |
| 3 | $25,000 | Standard — full diversification |

---

## Documentation

- **[USER_JOURNEY.md](./USER_JOURNEY.md)** — Complete walkthrough of every screen, every backend job, and every safety guardrail
- **[plans/ARCHITECTURE.md](./plans/ARCHITECTURE.md)** — System design and tech stack decisions
- **[plans/ROADMAP.md](./plans/ROADMAP.md)** — Build phases and feature timeline
- **[plans/DEPLOYMENT.md](./plans/DEPLOYMENT.md)** — VM deployment with Caddy and systemd
- **[plans/LIVE_TRADING_CHECKLIST.md](./plans/LIVE_TRADING_CHECKLIST.md)** — Pre-live trading safety checklist
- **[API docs](http://localhost:8420/docs)** — Auto-generated FastAPI OpenAPI docs (when running locally)

---

## Contributing

This is a personal trading system, but if you spot bugs or have ideas, open an issue. All changes must pass the full test suite:

```bash
cd backend
pytest tests/ -v
```

---

## License

MIT — Use at your own risk. This is not financial advice. Past performance does not guarantee future results. Always paper trade first.

---

*Stradegy v2.0.0 — Built for autonomous, self-improving, risk-managed algorithmic trading.*
