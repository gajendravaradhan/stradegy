# Stradegy — User Journey & Business Rundown

## What Is Stradegy?

Stradegy is an **autonomous algorithmic trading system** that runs on your own hardware (NAS or server), connects to Alpaca for trade execution, and surfaces everything through a mobile-first React PWA. It is designed for a single user — you — who wants to delegate day-to-day trading decisions to a bot while retaining full visibility and kill-switch control.

The philosophy is:

> **Research signals → Ensemble strategy voting → Risk-managed execution → Continuous self-improvement**

---

## The Backend: What Happens Automatically

You do not interact with the backend directly, but this is what it does for you 24/7.

### 1. Data Pipeline

- **53 US equities** are tracked (AAPL, MSFT, GOOGL, etc.) with historical OHLCV data backfilled up to 20 years.
- Every evening at **20:00 UTC**, the backend runs an incremental data refresh to pull the latest prices.
- All data lives in a local SQLite database (`backend/data/stradegy.db`).

### 2. Research Pipeline (Signal Generation)

Scheduled jobs scan for "Hidden Gems" using three sources:

| Source | What It Scans |
|--------|---------------|
| **Reddit** | r/wallstreetbets, r/stocks — mentions and sentiment |
| **SEC Filings** | Insider transactions and 8-K events |
| **Finnhub News** | Sentiment scoring on financial news |
| **Technical Indicators** | Computed from price data (RSI, MACD, Bollinger Bands, ADX) |

Results are aggregated into a **Gem Signal** with:
- A **score** from 0–100
- A **classification** (High, Medium, or Low conviction)
- Per-source breakdowns (Reddit, SEC, News, Technical)

### 3. Strategy Engine

Three individual strategies vote on whether to enter or exit a position:

| Strategy | Logic |
|----------|-------|
| **Mean Reversion** | Buys oversold assets using RSI + Bollinger Bands |
| **Momentum Breakout** | Buys breakouts above 20-day highs with volume + ADX confirmation |
| **Earnings Momentum** | Buys MACD crossovers with volume confirmation |

An **Ensemble** requires at least **2 of 3 strategies to agree** (configurable) before a trade is considered. This consensus mechanism reduces false signals and whipsaws.

### 4. Risk Management

Before any trade is submitted, the **RiskManager** enforces:

- **Position Sizing**: Calculates shares based on 3% risk per trade and ATR-based stop losses. Caps any single position at 25% of equity.
- **Max Drawdown**: If the account drops 20% from its peak, a kill-switch immediately halts all trading.
- **PDT (Pattern Day Trader) Guard**: Monitors the 3-day-trade limit for accounts under $25,000 and blocks violations.
- **Correlation Check**: Warns if you are over-concentrated in highly correlated tickers (threshold > 0.8).
- **Tax Reserve**: Automatically sets aside 30% of realized short-term gains for tax obligations.

### 5. Execution (Alpaca)

- Trades are sent to **Alpaca** (paper by default, live when you graduate).
- Paper mode uses fake money but real market data and real order routing logic.
- The backend can run in two modes:
  - **Semi-Autonomous**: Bot suggests trades; you approve or reject via Telegram.
  - **Full-Autonomous**: Bot executes trades without asking.

### 6. Self-Improvement System

Every **Sunday at 02:00 UTC**, the bot runs a ratchet loop:

1. Reviews the last week’s trades.
2. Calculates win rate, Sharpe ratio, and drawdown.
3. Compares live results to backtest expectations.
4. If a strategy underperforms, it updates a "Skillbook" with a rule adjustment.
5. If the ensemble improves, it versions the new configuration. If it degrades, it rolls back to the last known good state.

This ensures the bot gets better over time — or at least does not get worse.

### 7. Walk-Forward Backtesting

- The backtester uses **rolling windows**: it trains on 1 year of data, tests on 3 months, then rolls forward.
- This is "anti-cheat" — the model never sees future data during testing.
- You can trigger a backtest manually for any ticker and strategy via the API.

---

## The Frontend: PWA Screens

When you open the app (at `http://localhost:5173` or your Cloudflare HTTPS tunnel on your phone), you see a 5-tab mobile app.

### Tab 1 — Home / Dashboard

The Dashboard is your command center. It refreshes every **30 seconds**.

- **Total Equity**: Your current Alpaca account value.
- **Day P&L**: Today's profit/loss, colored green (profit) or red (loss).
- **Stat Cards**:
  - Buying Power
  - Tax Reserve
  - Day P&L
- **AAPL Sparkline Chart**: A 90-day price trend rendered as a lightweight SVG sparkline. It updates every 60 seconds.
- **Open Positions**: Lists all current holdings with unrealized P&L per position.
- **Paper/Live Badge**: A pill in the top-right shows whether you are in paper or live mode.
- **Recent Activity**: Placeholder for an upcoming trade log feed.

### Tab 2 — Hidden Gems (Alerts)

This page surfaces trade ideas discovered by the research pipeline. It refreshes every **60 seconds**.

Each Gem card displays:
- **Ticker symbol**
- **Classification** (High / Medium / Low) as a colored badge
- **Total score** (0–100)
- **Per-source breakdown**:
  - Reddit score
  - SEC score
  - News score
  - Technical score

If no gems are found, an empty state explains: "The research pipeline will scan Reddit, SEC filings, and news."

### Tab 3 — Portfolio

Your holdings and financial summary.

- **Total Equity** summary at the top.
- **Positions / Trade History toggle**:
  - **Positions tab**: Lists each holding with:
    - Shares
    - Average entry price
    - Market value
    - Unrealized P&L % (with green up-arrow or red down-arrow)
  - **Trade History tab**: Placeholder for completed trades (populated from trade logs).
- **Tax Summary card**:
  - Realized Gains
  - Tax Reserve (30%)
  - Available after tax

### Tab 4 — Strategy Engine

Control and inspect the algorithmic strategies.

- **Ensemble Status**: Shows whether the ensemble is active, plus configurable thresholds:
  - Minimum Confidence
  - Minimum Agreement (how many strategies must agree)
- **Individual Strategies** (Mean Reversion, Momentum Breakout, Earnings Momentum):
  - **Toggle button**: Turn a strategy on or off. The icon switches from grey (`ToggleLeft`) to green (`ToggleRight`).
  - **Weight slider**: Adjust the strategy’s vote weight from 0% to 100%.
  - **Sharpe ratio** and **P&L** displayed per strategy.
- Footer note: "Self-improvement cycle runs weekends."

> **Note**: Strategy toggles are currently local React state and are not yet persisted to the backend.

### Tab 5 — Settings

Configure how the bot behaves.

- **Trading Mode**:
  - **Paper Trading** (default): Fake money. Safe to experiment.
  - **Live (Alpaca)**: Real money. Only toggle after graduating from the checklist.
- **Autonomy Mode**:
  - **Semi-Autonomous**: Bot suggests trades; you approve or reject.
  - **Full-Autonomous**: Bot trades without asking.
- **Risk Parameters** (display-only; configured in `.env`):
  - Max Drawdown: 20%
  - Risk Per Trade: 3%
  - Max Positions: 1
  - Stop ATR Multiplier: 1.5x
- **Tax Settings**:
  - Short-Term Rate: 30%
  - Long-Term Rate: 15%
- App version shown at bottom.

---

## How a Typical Day Looks

| Time (UTC) | What Happens |
|------------|--------------|
| **13:30 (Mon–Fri)** | Market open scan: research pipeline runs a deep scan for gems. |
| **13:45 – 20:00 (Mon–Fri)** | Incremental scan every 15 minutes: updates news and sentiment. |
| **20:00 (Mon–Fri)** | Market close scan + daily data refresh: backfills OHLCV for all tickers. |
| **20:00** | RiskManager evaluates P&L and drawdown status. |
| **20:00** | If in full-autonomous mode, the ensemble may submit orders. |
| **02:00 (Sunday)** | Self-improvement cycle runs: evaluates performance and adjusts rules. |
| **16:00 (Saturday)** | Weekend deep research scan (SEC filings, Reddit deep dives). |

---

## Single-Command Bootup

From the project root, run:

```bash
./start.sh
```

This starts:
- **Backend**: FastAPI on `http://localhost:8420`
- **Frontend**: Vite dev server on `http://localhost:5173`

The backend auto-seeds 53 tickers into the database on first startup.

---

## API Endpoints

You can interact with the system programmatically via these REST endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/health` | Is the system up? |
| `GET` | `/api/account/summary` | Quick equity / mode summary |
| `GET` | `/api/portfolio` | Real-time Alpaca positions and equity |
| `GET` | `/api/alerts` | Hidden gems list |
| `GET` | `/api/strategies` | Strategy config and weights |
| `GET` | `/api/settings` | Current risk / tax / mode config |
| `POST` | `/api/settings` | Update mode or autonomy |
| `POST` | `/api/backtest/run` | Run walk-forward backtest |
| `GET` | `/api/backtest/strategies` | List available backtest strategies |
| `GET` | `/api/data/tickers` | List all tracked tickers |
| `POST` | `/api/data/backfill` | Backfill historical data |
| `POST` | `/api/data/incremental` | Incremental data update |
| `GET` | `/api/data/tickers/{symbol}/range` | Date range available for a ticker |
| `GET` | `/api/data/tickers/{symbol}/sparkline` | Sparkline data for a ticker |
| `GET` | `/api/data/tickers/{symbol}/ohlcv` | Raw OHLCV candles for a ticker |

---

## Security & Safety Guardrails

| Guardrail | How It Works |
|-----------|--------------|
| **Paper by default** | The `.env` flag `PAPER_TRADING=true` is the only gateway to live trading. You cannot accidentally trade real money. |
| **Kill switch** | If the account drops 20% from peak, all trading halts immediately. |
| **PDT guard** | Prevents the 3-day-trade limit violation for accounts under $25,000. |
| **Visual key distinction** | Alpaca **live** keys start with `AK`; **paper** keys start with `PK`. |
| **API key protection** | All keys live in `backend/.env`, which is in `.gitignore` and never committed. |

---

## What You Need to Provide

To make the app fully operational, paste these three values into `backend/.env`:

1. **Finnhub API Key** (free at [finnhub.io](https://finnhub.io)) — for news sentiment and gem signals.
2. **Alpaca API Key** (free paper account at [alpaca.markets](https://alpaca.markets)) — for portfolio and trade execution.
3. **Alpaca Secret Key** — paired with the API key above.

Reddit is **optional** and currently blocked by Reddit's Responsible Builder Policy. The app gracefully skips Reddit scanning when credentials are missing.

---

## Live Trading Graduation

Before switching to live trading, complete the checklist in `plans/LIVE_TRADING_CHECKLIST.md`:

- 4+ weeks of successful paper trading
- Backtest Sharpe ratio > 0.5 and max drawdown < 20%
- Self-improvement cycle has run at least once
- All 117 unit/integration tests passing
- Docker image builds successfully
- PWA installs on your phone via HTTPS
- Alpaca live account funded with $200 minimum
- `PAPER_TRADING=false` set in `.env`

**Target Account Size Progression:**

| Phase | Capital | Strategy |
|-------|---------|----------|
| 1 | $200 | Micro — 1 position, 3% risk |
| 2 | $2,500 | Small — 2–3 positions |
| 3 | $25,000 | Standard — full diversification |

Move to the next phase only after the current phase shows 2+ months of profitable, stable performance with drawdowns under the limit.

---

## Next Steps

1. Ensure your `backend/.env` contains valid Finnhub and Alpaca paper keys.
2. Restart the app so it picks up the new environment variables:
   ```bash
   ./start.sh
   ```
3. Open `http://localhost:5173` on your phone or browser.
4. Watch the **Dashboard** populate with real Alpaca paper equity.
5. Monitor the **Alerts** page as Finnhub news scans run throughout the trading day.

---

*Stradegy v2.0.0 — Built for autonomous, self-improving, risk-managed algorithmic trading.*
