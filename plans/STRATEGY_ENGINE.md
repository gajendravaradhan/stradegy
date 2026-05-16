# Strategy Engine — Trading Logic

## Overview

The strategy engine runs three independent strategies in parallel. An ensemble layer dynamically
allocates capital to each based on 20-day rolling Sharpe ratio. All strategies are swing-only
(never open and close the same day) to avoid Pattern Day Trading (PDT) violations.

## Strategy Matrix

| Strategy | Signal Type | Hold Period | Best Regime | Risk Level |
|----------|------------|-------------|-------------|------------|
| Mean Reversion | Counter-trend | 1-4 days | Range-bound / choppy | Low |
| Momentum Breakout | Trend-following | 2-5 days | Trending (ADX > 25) | Medium |
| Earnings Momentum | Event-driven | 3-15 days | Post-earnings season | Medium-High |

---

## Strategy 1: Mean Reversion

### Thesis
Stocks that are oversold (RSI < 30) but have strong fundamentals will revert to their mean.
Enter near support, exit at resistance. The safest strategy, ideal for micro-accounts.

### Entry Conditions (ALL required)
1. RSI(14) < 30 (oversold condition)
2. Price > 200-day SMA (long-term uptrend intact — buying the dip, not catching a falling knife)
3. Volume > 50-day average (capitulation volume confirms reversal point)
4. Bollinger Bands: price near or below lower band (2 stdev)
5. Gem detector score > 40 (fundamentals are solid)
6. No negative news in last 24 hours (FinBERT score > -0.3)

### Exit Conditions (ANY triggers)
1. **Stop Loss:** Price < entry - (1.0 * ATR) — tight stop for mean reversion
2. **Take Profit:** RSI crosses above 55 OR price touches 20-day SMA
3. **Time Stop:** Hold period > 4 trading days
4. **Emergency Stop:** Account drawdown > 15% — close all positions

### Risk Parameters
- Risk per trade: 1.5-2% of account (tighter — smaller, more frequent wins)
- Position size = (account_value * risk_pct) / (entry - stop_price)
- Minimum position value: $5 (Alpaca fractional support)

---

## Strategy 2: Momentum Breakout

### Thesis
Stocks breaking above recent resistance on higher-than-average volume, confirmed by social
buzz and positive news sentiment, tend to continue moving upward for several days.

### Entry Conditions (ALL required)
1. Price > 20-day high (confirmed breakout, not a false signal)
2. Volume > 1.5x 20-day average volume (volume confirms conviction)
3. ADX > 25 (market is trending, not choppy)
4. MACD histogram positive and rising (momentum confirmation)
5. At least ONE sentiment confirmation:
   - Reddit mention velocity > 2x 7-day average
   - FinBERT news sentiment > 0.6 bullish
6. Gem detector score > 50

### Exit Conditions (ANY triggers)
1. **Stop Loss:** Price < entry - (1.5 * ATR)
2. **Take Profit:** Price > entry + (3 * ATR) — 1:2 risk/reward
3. **Trailing Stop:** Price < highest_since_entry - (2 * ATR)
4. **Time Stop:** Hold period > 5 trading days
5. **Trend Decay:** ADX drops below 20 — fading momentum
6. **Emergency Stop:** Account drawdown > 15%

### Risk Parameters
- Risk per trade: 2-3% of account
- Wider stops than mean reversion (momentum can retrace before continuing)

---

## Strategy 3: Earnings Momentum

### Thesis
Companies that beat earnings estimates, raise guidance, and receive analyst upgrades experience
positive post-earnings drift in the following weeks. Enter after the initial gap, ride the re-rating.

### Entry Conditions (ALL required)
1. Earnings released within last 3 trading days
2. EPS beat > 10% above consensus
3. Revenue beat > 5% above consensus
4. Guidance raised (next quarter or full year)
5. At least 2 analyst upgrades post-earnings
6. Price has NOT gapped > 15% from pre-earnings close (avoid chasing)
7. Gem detector score > 55

### Exit Conditions (ANY triggers)
1. **Stop Loss:** Price < pre-earnings close (gap fill risk)
2. **Take Profit:** Price > entry + (5 * ATR) OR hold > 20 days
3. **Trailing Stop:** Price < highest_since_entry - (3 * ATR)
4. **Signal Degradation:** Any analyst downgrade post-earnings
5. **Emergency Stop:** Account drawdown > 15%

### Risk Parameters
- Risk per trade: 2-3% of account
- Wider stops needed due to elevated post-earnings volatility

---

## Ensemble Layer

### Dynamic Strategy Weighting

Every week, strategies are re-weighted based on 20-day rolling Sharpe ratio:

```
weight_i = max(0, rolling_sharpe_i) / sum(max(0, rolling_sharpe_j) for all j)
```

Rules:
- Negative Sharpe → weight = 0 (strategy deactivated)
- Minimum allocation: 20% floor (lower allocations don't meaningfully move the needle)
- Deactivated strategies are monitored — if Sharpe recovers, they reactivate
- Monthly Optuna re-optimization of each strategy's parameters

### Capital-Adaptive Tiers

| Account Size | Max Positions | Active Strategies | Risk/Trade |
|-------------|:------------:|-------------------|:----------:|
| $200 - $500 | 1 | Mean Reversion only | 3% |
| $500 - $2,000 | 2 | MR + best of MB/EM | 2% |
| $2,000 - $5,000 | 3 | All 3 strategies | 2% |
| $5,000 - $10,000 | 4 | All 3 + scaling | 2% |
| $10,000 - $25,000 | 5 | Full ensemble | 1.5% |
| $25,000+ | 6+ | Day trades unlocked | 1% |

### Position Selection Priority (Capital-Constrained)

When the account can only hold N positions:
1. Highest gem scorer tickers get priority
2. Within a strategy, highest risk/reward ratio gets priority
3. New gem must score higher than the lowest-scoring current position to trigger a swap

---

## Pre-Trade Execution Checks

Before ANY order is submitted:
1. **PDT Check:** Entry date != exit date for this position (no same-day round-trip)
2. **Buying Power:** Trade cost + estimated slippage < available buying power
3. **Tax Reserve:** Post-trade available capital >= current tax reserve balance
4. **Drawdown Limit:** Current DD < 15% (emergency stop threshold)
5. **Market Hours:** Regular trading session is active (9:30 AM - 4:00 PM ET)
6. **News Blackout:** No pending material event (earnings, FDA decision, merger vote)
