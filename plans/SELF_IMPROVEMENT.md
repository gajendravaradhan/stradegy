# Self-Improvement — The Recursive Learning Loop

## Inspiration

The self-improvement system is adapted from the open-source framework
[kayba-ai/recursive-improve](https://github.com/kayba-ai/recursive-improve).
The author's key finding after months of experimentation: **the bottleneck isn't model
reasoning — it's the trace/analyze/fix tooling layer.** You don't need a complex
multi-agent system. You need structured traces, atomic skill extraction with quality gates,
metric-driven evaluation, and a ratchet loop where only improvements survive.

## The Core Loop

```
Every Weekend (Cron Job):

  1. TRACE ANALYSIS ──> Analyze last week's trade traces
     - 6-phase structured analysis (discover→criteria→survey→categorize→deep-dive→synthesize)
     - Identify: which trades won? why? which lost? what patterns?

  2. ATOMIC SKILL EXTRACTION ──> From analysis, extract atomic trading rules
     - "Set stop-loss at 1.5 ATR, not 2 ATR" (evidence: 4 trades hit 2 ATR stop)
     - Quality gates: reject vague rules ("be careful"), enforce atomicity

  3. METRICS BASELINE ──> Measure current performance
     - Sharpe, win-rate, profit-factor, max-DD, avg-win/L
     - Compare against prior week's baseline

  4. OPTIMIZE ──> Walk-forward optimize on recent 3 months
     - Optuna tunes: stop distance, entry threshold, hold period
     - Validate on out-of-sample recent 2 weeks

  5. RATCHET ──> Keep or Revert
     - IF new params beat baseline → KEEP (bump strategy version)
     - IF worse or equal → REVERT (strategy unchanged)

  6. NOTIFY ──> Telegram report
     "Weekly Review: P&L +$X.XX | Win rate 62%→67% | Strategy A weight 70%→80%"
```

---

## Stage 0: Trace Collection

Every trade decision is logged as a structured JSON trace in `eval/traces/`:

```json
{
  "run_id": "2026-05-13-09-45-abc123",
  "timestamp": "2026-05-13T09:45:00-04:00",
  "action": "enter",
  "strategy": "mean_reversion",
  "ticker": "PLUG",
  "gem_score": 87,
  "signals": {
    "rsi": 28,
    "bollinger_position": -2.1,
    "volume_vs_avg": 1.8,
    "reddit_mentions_1h": 45,
    "reddit_sentiment": 0.78,
    "finbert_sentiment": 0.83,
    "insider_buys_30d": 3,
    "revenue_growth_yoy": 0.32
  },
  "decision": {
    "entry_price": 4.20,
    "shares": 3,
    "stop_loss": 3.90,
    "take_profit": 5.10,
    "position_size_usd": 12.60
  }
}
```

```json
{
  "run_id": "2026-05-13-09-45-abc123",
  "timestamp": "2026-05-15T14:30:00-04:00",
  "action": "exit",
  "ticker": "PLUG",
  "exit_reason": "stop_loss",
  "entry_price": 4.20,
  "exit_price": 3.90,
  "pnl": -0.90,
  "pnl_pct": -0.071,
  "holding_days": 2
}
```

---

## Stage 1: 6-Phase Trace Analysis

Every weekend, the analyzer processes the week's traces through a structured 6-phase pipeline:

### Phase 1: Discover
- Read all trace files
- Map data shape: how many runs, what strategies, what outcomes
- Build inventory: trades entered, exited, still open

### Phase 2: Derive Evaluation Criteria
- What should a "good" trade look like?
- What signals correlated with wins? With losses?
- Create specific criteria to evaluate each trade

### Phase 3: Survey
- Read EVERY trace (trading produces modest counts — 0-10 per week)
- For each trade: what happened, what went right, what went wrong
- Score each trade against evaluation criteria

### Phase 4: Categorize
- Group trades by strategy, outcome (win/loss), and exit reason
- Identify: most common failure pattern, most common success pattern

### Phase 5: Deep-Dive
- For losing trades: read the full raw trace
- Verify: did the data actually support the entry decision?
- Root cause: was it a bad signal, bad timing, bad exit, or bad luck?

### Phase 6: Synthesize
- Combine all findings into atomic learnings
- Each learning: one concept, evidence-backed, severity-tagged

### Output: `eval/stage0_trace_analysis.md`

```markdown
# Trace Analysis — Week of 2026-05-11

## Summary
- 4 trades entered, 3 closed, 1 open
- 2 wins (+$4.20, +$3.10), 1 loss (-$0.90)
- Win rate: 66%, Net P&L: +$6.40

## Extracted Learnings
| # | Learning | Evidence | Severity |
|---|----------|----------|----------|
| 1 | Mean-rev exits too early — RSI crossed 55 but trend continued | PLUG sold at 3.90, next day hit 4.80 | Medium |
| 2 | Momentum stops at 1.5 ATR too tight — 2 of 3 winners hit stop | RGTI stopped at -2%, then rebounded +8% | High |
```

---

## Stage 2: Atomic Skill Extraction

Raw learnings are transformed into atomic, actionable trading rules with quality gates:

### Quality Gates

| Gate | Pass Criteria | Example Failure |
|------|--------------|-----------------|
| **Atomicity** | One concept per rule | FAIL: "Improve entries and exits" |
| **Imperative** | "DO X when Y", not "should X" | FAIL: "Consider exits more carefully" |
| **Measurable** | Can validate against metrics | FAIL: "Feel more confident" |
| **Evidence-Backed** | Cites specific trace evidence | FAIL: No trace reference |
| **Non-Meta** | Actionable, not commentary | FAIL: "Be careful about losses" |

### Output: `eval/skillbook.json`

```json
{
  "skills": {
    "mr-stop-001": {
      "id": "mr-stop-001",
      "section": "mean_reversion",
      "content": "Use 1.0 ATR stop for mean-reversion entries instead of 1.5 ATR",
      "evidence": "trace_2026-05-11-abc.json — PLUG exit at 2 ATR stop, rebounded to +14% next day",
      "helpful": 0,
      "harmful": 0,
      "status": "active"
    }
  }
}
```

### Atomicity Scoring

```
Base score: 1.0
- Deduct 0.15 per "and", "also", "plus"
- Deduct 0.20 per vague term ("appropriate", "proper", "various")
- Deduct 0.05 per word over 15

Score < 0.85 → SPLIT into multiple skills
Score < 0.40 → REJECT (too vague)
```

---

## Stage 3: Ratchet Loop

The ratchet loop ensures only improvements survive. Regression is impossible.

### How It Works

```
┌──────────────────────────────────────────────┐
│  RATCHET ITERATION                            │
│                                               │
│  1. Measure current baseline metrics          │
│  2. Apply proposed parameter changes          │
│  3. Paper-trade for 3 days (or 20 trades)     │
│  4. Measure new metrics                       │
│  5. IF new > baseline:                        │
│       - COMMIT changes                        │
│       - Bump strategy version                 │
│       - Update baseline = new                 │
│     ELSE:                                     │
│       - REVERT changes                        │
│       - Log: why it failed                    │
│  6. Repeat                                    │
└──────────────────────────────────────────────┘
```

### Implementation

```python
class Ratchet:
    def __init__(self, strategy, baseline_metrics):
        self.strategy = strategy
        self.baseline = baseline_metrics
        self.history = []

    def iterate(self, new_params, paper_trading_days=3):
        # Snapshot before
        before_metrics = self.strategy.current_metrics()

        # Apply changes
        self.strategy.update_params(new_params)

        # Paper trade to validate
        paper_results = self.paper_trade(days=paper_trading_days)
        after_metrics = paper_results.metrics

        # Keep or revert
        if self.is_improvement(before_metrics, after_metrics):
            self.strategy.commit(new_params)
            self.history.append({
                'action': 'KEEP',
                'before': before_metrics,
                'after': after_metrics,
                'params': new_params,
                'version': self.strategy.bump_version()
            })
        else:
            self.strategy.revert()
            self.history.append({
                'action': 'REVERT',
                'before': before_metrics,
                'after': after_metrics,
                'params': new_params
            })

    def is_improvement(self, before, after):
        # Multi-metric check
        sharpe_improved = after.sharpe > before.sharpe * 1.02
        dd_safe = after.max_drawdown < 25.0
        return sharpe_improved and dd_safe
```

### Strategy Versioning

```
strategies/
├── v1_baseline/    # Initial strategy
├── v2_stop_fix/    # After mean-rev stop width reduction
├── v3_entry_timing/ # After RSI threshold adjustment
└── v4_current/     # Active strategy (symlink or pointer)
```

---

## Weekly Automation Schedule

| When | What |
|------|------|
| Saturday 8:00 AM ET | Full trace analysis + skill extraction |
| Saturday 12:00 PM | Optuna parameter optimization |
| Saturday 6:00 PM | Ratchet: apply best params, paper trade |
| Sunday 8:00 AM | Ratchet: eval paper results, keep/revert |
| Sunday 6:00 PM | Telegram weekly report to user |

---

## Key Design Principles

1. **Trace Everything:** Every trade decision is a structured trace. No trace = no improvement.
2. **Atomic Skills:** One concept per skill. No compound rules.
3. **Evidence Over Intuition:** No parameter change without a trace-backed reason.
4. **Keep or Revert:** Only improvements survive. Regression is rolled back instantly.
5. **Versioned Strategies:** Never overwrite the working strategy without a rollback path.
6. **Context Compression:** Store pre-digested summaries, not raw tick data. Prevents memory bloat.
