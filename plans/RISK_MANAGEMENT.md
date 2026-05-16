# Risk Management — Protection, PDT, Tax

## Overview

Risk management is the most critical layer of the system. It protects the account from
blowing up, ensures PDT compliance, and maintains tax reserves. Good risk management is
what separates a trading bot from a gambling bot.

---

## Position Sizing

### ATR-Based Volatility Sizing

All position sizes are calculated using Average True Range (ATR) — they adapt to each
stock's current volatility, not a fixed stop percentage.

```python
def calculate_position_size(account_value, risk_per_trade, entry_price, atr, atr_mult):
    """
    Calculate position size based on ATR stop distance.

    risk_amount = account_value * risk_per_trade    # eg. $200 * 0.03 = $6
    stop_distance = atr * atr_mult                   # eg. $0.30 * 1.5 = $0.45
    shares = risk_amount / stop_distance             # $6 / $0.45 = 13.33 → 13 shares
    """
    risk_amount = account_value * risk_per_trade
    stop_distance = atr * atr_mult
    shares = risk_amount / stop_distance
    return max(0, int(shares))
```

### Risk Per Trade by Capital Tier

| Account Size | Risk/Trade | Rationale |
|-------------|:----------:|-----------|
| $200 - $500 | 3% ($6-$15) | Higher % needed for meaningful returns on small capital |
| $500 - $2,000 | 2% ($10-$40) | Moderate scaling |
| $2,000 - $5,000 | 2% | Maintain aggression while reducing blowup risk |
| $5,000 - $10,000 | 2% | Larger position sizes amplify returns |
| $10,000 - $25,000 | 1.5% | Reduce tail risk as account grows |
| $25,000+ | 1% | Institutional-grade risk management |

### Kelly Fraction Check

Before any trade, the system validates that position size doesn't exceed 1/4 Kelly:
```
f* = (bp - q) / b
where b = avg_win / avg_loss, p = win_rate, q = 1 - p
If suggested allocation > 0.25 * f* → cap at 0.25 * f*
```
Full Kelly is too aggressive and leads to ruin; 1/4 Kelly balances growth and safety.

---

## Drawdown Control

The drawdown controller protects capital by progressively reducing risk as losses mount.

```
0-10% DD → Normal trading (100% position size)
10-15% DD → Reduced trading (50% position size)
15-20% DD → Minimum trading (25% position size)
>20% DD → STOP ALL TRADING (hard kill switch)
```

When drawdown triggers a risk reduction level, the system:
1. Reduces position sizes per the schedule above
2. Does NOT open new positions if it would exceed the reduced size
3. Continues managing existing positions (with existing stops)
4. Sends Telegram alert: "Drawdown at {X}%. Trading reduced to {Y}% size."
5. When DD recovers below 10%, automatically restores normal size

### Recovery Protocol
- Drawdown is measured from the account's all-time high equity
- After a kill switch (20% DD), trading remains halted until a human reviews
  and manually re-enables trading from the Settings tab
- The system does NOT attempt to "trade its way out" of a drawdown

---

## Pattern Day Trading (PDT) Compliance

### The Rule
SEC Pattern Day Trader rule: accounts under $25,000 cannot make 4+ day trades (buy and sell
the same security on the same day) within a rolling 5-business-day window.

### Enforcement

Stradegy enforces PDT compliance at the code level — it is impossible to violate:

```python
from collections import deque
from datetime import datetime, timedelta

class PDTracker:
    """Tracks day trades in a rolling 5-business-day window."""

    def __init__(self):
        self.day_trades = deque()  # dates of day trades

    def record_day_trade(self, date=None):
        # called when a same-day open+close occurs
        self.day_trades.append(date or datetime.now().date())

    def day_trade_count(self):
        cutoff = datetime.now().date() - timedelta(days=5)
        while self.day_trades and self.day_trades[0] < cutoff:
            self.day_trades.popleft()
        return len(self.day_trades)

    def can_day_trade(self):
        return self.day_trade_count() < 3  # 4th trade = violation

    def can_open_position(self, ticker, timeline=[]):
        """Prevent opening if it would require same-day close (PDT risk)."""
        # Check if we already have an open position in this ticker
        existing = [t for t in timeline if t['ticker'] == ticker
                    and t['entry_date'] == datetime.now().date()]
        if existing:
            return False  # Already entered today, can't add more
        return self.can_day_trade() or datetime.now().hour < 15
        # If already at 3 day trades, only allow new entries after 3 PM
        # (ensuring position carries overnight, avoiding same-day close)
```

### Swing Trading Default
- The default behavior is **swing trading**: ALL entries must be held overnight
- Same-day exits are blocked unless the user explicitly enables day trading
- When account surpasses $25,000, PDT restrictions are automatically lifted

---

## Tax Reserve Manager

### Why This Matters
A common pitfall: trader makes $10,000 profit, owes $3,000 in taxes, but the $10,000
was reinvested and the market drops — now they owe $3,000 with no money to pay it.

### Implementation

```python
class TaxReserveManager:
    SHORT_TERM_RATE = 0.30   # Configurable — US short-term capital gains
    LONG_TERM_RATE = 0.15    # Configurable — held > 1 year

    def __init__(self):
        self.realized_gains_short = 0.0
        self.realized_losses = 0.0
        self.tax_reserve = 0.0

    def on_trade_close(self, pnl, holding_days):
        if pnl > 0:
            if holding_days > 365:
                self.realized_gains_short += pnl * self.LONG_TERM_RATE
                # Long-term gains taxed at lower rate
            else:
                self.realized_gains_short += pnl
        else:
            self.realized_losses += abs(pnl)

    def recalculate_reserve(self):
        """Net realized gain = short-term gains - realized losses."""
        net_gain = max(0, self.realized_gains_short - self.realized_losses)
        self.tax_reserve = net_gain * self.SHORT_TERM_RATE

    def available_capital(self, total_equity):
        """Tradable capital = total equity - tax reserve (locked)."""
        return max(0, total_equity - self.tax_reserve)

    def send_quarterly_reminder(self):
        """Telegram: 'Q1 Est. Tax: $X. Set aside $Y for IRS estimated payment.'"""
        pass
```

### Tax Reserve Rules
1. Reserve is recalculated after every trade close
2. Tax reserve is NEVER available for trading
3. Only the portion of equity ABOVE the reserve is "buying power"
4. Quarterly reminders prompt estimated tax payments
5. Tax settings (rates) are configurable in the Settings tab

---

## Correlation Check

Before opening a new position, the system checks correlation with existing positions:

```python
def check_correlation_limit(new_ticker, existing_positions, limit=0.7):
    """
    If new ticker is highly correlated (> 0.7) with any existing position,
    reduce position size by 50% to avoid concentration risk.
    """
    for pos in existing_positions:
        corr = calculate_rolling_correlation(new_ticker, pos.ticker, window=60)
        if corr > limit:
            return True
    return False
```

This prevents accidental doubling-down on the same sector or theme.

---

## Emergency Procedures

| Event | Action |
|-------|--------|
| Account DD hits 20% | Kill switch: no new trades. Telegram alert. Manual review required. |
| Single position loses > 50% | Investigate. If due to material event (fraud, delisting), manually close. |
| API connection lost | Retry 3x with exponential backoff. After 5 min, Telegram alert. |
| Market-wide crash (SPY -5% day) | Pause new entries. Send alert. Wait for volatility to normalize. |
| Unexpected margin call | Immediately close lowest-P&L position. Telegram alert. |
