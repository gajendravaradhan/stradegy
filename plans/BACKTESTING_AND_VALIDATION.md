# Backtesting & Validation

## Philosophy

Every strategy must prove itself on historical data BEFORE a single real dollar is risked.
We use strict walk-forward methodology to eliminate look-ahead bias. No hindsight,
no overfitting, no survivorship bias.

## Backtesting Engine

**Library:** vectorbt 0.28.2

Vectorbt was chosen for:
- **Speed:** Vectorized operations process entire OHLCV matrices at once — 1000x faster than event-driven engines
- **Walk-forward:** Built-in rolling optimization via `from_holding`
- **Optuna integration:** Native hyperparameter optimization
- **Metrics:** Sharpe, Sortino, Calmar, max drawdown, profit factor, win rate — all built-in

### Data Pipeline

```
yfinance EOD fetch → SQLite raw_ohlcv table → pandas DataFrame → vectorbt Portfolio
```

- **Resolution:** Daily bars (swing trading doesn't need intraday)
- **Universe:** Russell 2000 constituents + tickers surfaced by research pipeline
- **Date Range:** 2019-01-01 to most recent trading day
- **Adjustments:** Split-adjusted, dividend-adjusted close prices
- **Survivorship Bias:** Use historical index constituents, not current ones

---

## Walk-Forward Analysis

### Methodology

The key insight: **optimize parameters on in-sample data, validate on out-of-sample data
the optimizer has NEVER seen.** This is the gold standard for preventing overfitting.

### Anchored Walk-Forward

```
Data:  2019 ────────────────────────────────────────── 2025
       │                                                    │
       ├── Train 1 (2019-2022) ──┤ Test 1 (2023-Q1)       │
       │                          │                         │
       ├── Train 2 (2019-Q3 2022)─┤ Test 2 (2023-Q2)      │
       │                          │                         │
       ├── Train 3 (2019-2023) ──┤ Test 3 (2023-Q3)       │
       │                          │                         │
       ├── Train 4 (2019-Q3 2023)─┤ Test 4 (2023-Q4)      │
       │                          │                         │
       ├── Train 5 (2019-2024) ──┤ Test 5 (2024-H1)       │
       │                          │                         │
       ├── Train 6 (2019-H1 2024)─┤ Test 6 (2024-H2)      │
                                  │                         │
                                  ▼                         │
              Out-of-sample equity curve = sum of all test windows
```

- Train window: 3-4 years, expands forward (anchored)
- Test window: 3-6 months each
- Each window's test data becomes part of the next window's training data

### Implementation

```python
class WalkForwardAnalyzer:
    def __init__(self, data, train_years=3, test_months=6):
        self.data = data
        self.train_start = train_years * 252  # trading days
        self.test_len = test_months * 21

    def generate_windows(self):
        """Yield (train_data, test_data) pairs with no look-ahead."""
        for end_idx in range(self.train_start, len(self.data), self.test_len):
            train = self.data[:end_idx]
            test = self.data[end_idx:end_idx + self.test_len]
            if len(test) < 10:
                break
            yield train, test

    def run(self, strategy_class, param_space, n_trials=200):
        windows = list(self.generate_windows())
        oos_results = []
        params_history = []

        for train_data, test_data in windows:
            # OPTIMIZE on in-sample only
            best_params = self.optimize(strategy_class, train_data,
                                         param_space, n_trials)
            params_history.append(best_params)

            # VALIDATE on out-of-sample (no re-optimization)
            result = strategy_class(**best_params).backtest(test_data)
            oos_results.append(result)

        return self.aggregate(oos_results, params_history)

    def optimize(self, strategy_class, data, param_space, n_trials):
        study = optuna.create_study(direction='maximize')
        study.optimize(
            lambda t: self.objective(t, strategy_class, data, param_space),
            n_trials=n_trials
        )
        return study.best_params

    def objective(self, trial, strategy_class, data, param_space):
        params = {}
        for name, (suggest_method, *args) in param_space.items():
            params[name] = getattr(trial, suggest_method)(name, *args)
        result = strategy_class(**params).backtest(data)
        return result.sharpe_ratio  # Maximize risk-adjusted returns
```

---

## Optimization Parameters

| Parameter | Range | Type | Meaning |
|-----------|-------|------|---------|
| `rsi_period` | 5-30 | int | RSI lookback |
| `rsi_oversold` | 15-35 | int | Entry threshold |
| `rsi_overbought` | 65-85 | int | Exit threshold |
| `atr_stop_mult` | 1.0-3.0 | float | Stop distance (ATR units) |
| `atr_target_mult` | 2.0-5.0 | float | Target distance (ATR units) |
| `max_hold_days` | 2-10 | int | Max holding period |
| `volume_threshold` | 1.0-3.0 | float | Volume confirmation |

Rule of thumb: need 10+ trades per free parameter in each training window.

---

## Performance Metrics

### Primary (Optimization Target)
- **Sharpe Ratio:** (Return - Risk Free Rate) / Volatility → maximize
- **Sortino Ratio:** Sharpe variant using only downside deviation

### Secondary (Validation)
- **Win Rate:** % trades closed at profit → target > 50%
- **Profit Factor:** Gross profit / Gross loss → target > 1.5
- **Max Drawdown:** Largest peak-to-trough decline → must stay < 20%
- **Calmar Ratio:** Annualized return / Max drawdown → target > 1.0
- **Avg Win / Avg Loss Ratio:** Average winning trade / average losing trade → target > 1.5
- **Expectancy:** (Win Rate × Avg Win) - (Loss Rate × Avg Loss) → must be > 0

### Anti-Overfitting Checks
1. **Deflated Sharpe Ratio:** Adjusts for multiple hypothesis testing (trying 1000 param combos inflates Sharpe)
2. **Monte Carlo Shuffle:** Shuffle trade order 1000x — if shuffled results overlap with real, strategy is noise
3. **Parameter Stability:** If optimal param values jump wildly between windows, they're overfit
4. **OOS P&L Consistency:** Must be positive in > 70% of test windows

---

## Validation Gates

| Gate | Requirement | Severity |
|------|------------|----------|
| OOS Sharpe > 0.5 | Risk-adjusted returns passable | MUST PASS |
| OOS Profit Factor > 1.2 | Gross profit exceeds gross loss | MUST PASS |
| OOS Max DD < 25% | Drawdown within tolerance | MUST PASS |
| > 30 total OOS trades | Statistical significance | MUST PASS |
| OOS P&L > 0 in > 60% windows | Consistency across regimes | MUST PASS |
| Parameter stability | No wild parameter jumps | WARNING |
| Deflated Sharpe > 0 | Alpha survives multiple testing adjustment | WARNING |

---

## Pre-Live Graduation

### Paper Trading Validation (4 weeks minimum)

Before trading with real money:
1. Deploy strategy to Alpaca paper account
2. Run for 4+ weeks with realistic position sizes
3. Compare paper results to backtest distributions:
   - If paper P&L within 1 SD of backtest expected → GRADUATE TO LIVE
   - If paper P&L diverges significantly → INVESTIGATE (data error? slippage? regime change?)

### Slippage & Cost Modeling

Even though Alpaca is commission-free, the backtest assumes:
- **Slippage:** 0.1% per trade (realistic for small-cap stocks)
- **SEC Fee:** 0.0008% of sale proceeds
- **TAF Fee:** $0.000166 per share sold

After paper trading, compare modeled costs to actual fills and adjust if needed.
