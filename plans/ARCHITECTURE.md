# Stradegy — System Architecture

## Overview

Stradegy is a semi/fully-autonomous trading bot that researches investment opportunities like a
professional analyst, backtests strategies on historical data, trades via Alpaca Markets, and
recursively self-im/modeproves by analyzing its own trade traces.

The system is deployed as a single Docker container on a Ugreen NAS, serving a React PWA
(installed on the user's phone via "Add to Home Screen") for monitoring and control.

---

## Architecture Diagram

```
+--------------------------------------------------------------------+
|  Your Phone                         Your Ugreen NAS                |
|  +------------------+               +--------------------------+  |
|  |   Stradegy PWA   |--- HTTPS --->|   Docker Container        |  |
|  | (Add to Home Scr)|  Cloudflare   |  +--------------------+  |  |
|  |                  |   Tunnel      |  | FastAPI :8420      |  |  |
|  | [Dashboard]      |               |  |  serves API + PWA  |  |  |
|  | [Alerts]         |               |  +--------------------+  |  |
|  | [Portfolio]      |               |  | Trading Engine     |  |  |
|  | [Strategies]     |               |  | (APScheduler jobs) |  |  |
|  | [Settings]       |               |  +--------------------+  |  |
|  |                  |               |  | SQLite DB          |  |  |
|  |  Push Notif <----+---------------|  | /data/stradegy.db  |  |  |
|  +------------------+               |  +--------------------+  |  |
|                                     +--------------------------+  |
|                                                                     |
|  Telegram <------------ Gem Alerts + Daily P&L ---------------------+
+--------------------------------------------------------------------+
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Frontend** | React 18.3 + Vite | Fast HMR, excellent PWA ecosystem, small bundles |
| **Styling** | Tailwind CSS + shadcn/ui | Mobile-first, dark theme built-in, touch-optimized |
| **PWA** | vite-plugin-pwa | Manifest, service worker, offline caching, install prompt |
| **Routing** | React Router v7 | Tab-based navigation with deep linking |
| **Data Fetching** | TanStack Query v5 | Auto-caching, offline persistence, background refetch |
| **State** | Zustand v5 | Lightweight global state (auth, settings, WebSocket) |
| **Charts** | Tremor v4 (recharts) | Dark-themed financial charts, live updating |
| **Icons** | Lucide React | Clean tab bar and UI icons |
| **Backend** | FastAPI (Python 3.12+) | REST + WebSocket, async, serves static PWA |
| **Database** | SQLite + SQLAlchemy | Zero-config, single file, sufficient scale |
| **Scheduler** | APScheduler | Cron jobs for trading engine and weekly optimization |
| **Broker** | alpaca-py | Official Alpaca SDK, paper + live, fractional shares |
| **Market Data** | yfinance + finnhub-python | Free EOD/historical + real-time news/sentiment |
| **SEC Filings** | edgartools | Free, well-maintained, XBRL parsing, DataFrames |
| **Reddit** | PRAW + vader-sentiment | Subreddit streaming, ticker extraction, sentiment |
| **NLP** | FinBERT (HuggingFace) | Financial sentiment scoring, runs locally |
| **Backtesting** | vectorbt + optuna | Vectorized backtests, hyperparameter optimization |
| **Telegram** | python-telegram-bot | Gem alerts, daily P&L, execution notifications |
| **Deployment** | Docker Compose + Cloudflare Tunnel | NAS deployment, secure remote access |

---

## Data Flow

```
[Research Pipeline]                    [Strategy Engine]
Reddit + SEC + News                    Signal Generation
      |                                       |
      v                                       v
[Gem Detector] ──────> [Signal Confluence] ──> [Ensemble Weighting]
      |                                       |
      v                                       v
[Alerts/Telegram]                    [Execution Engine]
                                           |
                                           v
                                    [Alpaca Orders]
                                           |
                                           v
                                    [Trade Traces]
                                           |
                                           v
[Self-Improvement Loop] <── [Weekly Trace Analysis] <── [Trade Outcomes]
      |
      v
[Updated Strategy Rules] ──> [Backtest] ──> [Ratchet: Keep/Revert]
```

---

## Directory Structure

```
stradegy/
├── backend/                    # Python FastAPI
│   ├── main.py                 # FastAPI app entry point
│   ├── api/                    # REST + WebSocket endpoints
│   ├── engine/                 # Trading engine modules
│   │   ├── research/           # Reddit, SEC, news pipeline
│   │   ├── strategy/           # Signal generation, ensemble
│   │   ├── risk/               # Position sizing, PDT, tax
│   │   ├── execution/          # Alpaca client, orders
│   │   └── evolve/             # Self-improvement system
│   ├── db.py                   # SQLAlchemy models
│   ├── config.py               # Settings loader
│   └── pyproject.toml
│
├── frontend/                   # React PWA
│   ├── src/
│   │   ├── pages/              # Dashboard, Alerts, Portfolio, etc.
│   │   ├── components/         # Reusable UI components
│   │   ├── hooks/              # useWebSocket, useApi
│   │   ├── store/              # Zustand state
│   │   └── lib/                # API client
│   ├── public/                 # PWA manifest, icons
│   ├── package.json
│   └── vite.config.ts
│
├── eval/                       # Self-improvement artifacts
│   ├── traces/                 # Trade decision traces
│   ├── skillbook.json          # Atomic trading rules
│   └── ratchet_log.jsonl       # Keep/revert history
│
├── plans/                      # Project documentation (this folder)
├── data/                       # Persistent SQLite database
├── docker-compose.yml
├── Dockerfile
└── .gitignore
```

---

## Key Design Decisions

### 1. Single Deployable Unit
FastAPI serves both the REST/WebSocket API **and** the built PWA static files. One container,
one port, one command to run.

### 2. Mobile-First PWA
The React frontend is a PWA optimized for "Add to Home Screen" on phones. No native iOS/Android
development needed. 5-tab bottom navigation matches mobile OS conventions.

### 3. NAS as Server
Ugreen NAS runs Docker, so the stack deploys as a single container. Cloudflare Tunnel provides
secure HTTPS without port forwarding. The NAS runs 24/7 with minimal power draw.

### 4. Semi-Autonomous → Full-Autonomous Toggle
User can switch between modes from Settings tab without restart. Semi-auto mode adds
[Approve]/[Reject] buttons to gem alerts. Full-auto executes all trades without asking.

### 5. Capital-Adaptive Strategy
Strategy parameters (max positions, risk per trade, which strategies are active) auto-adjust
as account grows from $200 → $25,000+. Manual capital injections are detected and trigger
tier re-evaluation.

### 6. Tax-First Accounting
A tax reserve is computed from realized gains and set aside before calculating available
buying power. This prevents trading with money that is owed to the IRS.

### 7. Trace Everything
Every trade decision (entry signal, exit reason, P&L) is logged as structured JSON in
`eval/traces/`. These traces feed the weekly self-improvement loop.
