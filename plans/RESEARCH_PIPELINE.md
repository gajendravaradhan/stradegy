# Research Pipeline — Finding Hidden Gems

## Overview

The research pipeline is the "analyst brain" of Stradegy. It continuously scans Reddit, SEC
filings, and financial news to find undervalued, high-upside stocks before they become
mainstream. Every signal is evidence-backed — no fabrications, no hallucinations, no
assumptions without multi-source verification.

## Signal Sources

### 1. Reddit Scanner

**Library:** PRAW 7.8.1 (Python Reddit API Wrapper)

**Subreddits Monitored:**

| Subreddit | Purpose | Weight |
|-----------|---------|--------|
| `r/wallstreetbets` | High volume, sentiment extremes, early momentum | High |
| `r/stocks` | Fundamentals-oriented discussion, quality posts | High |
| `r/pennystocks` | Small-cap gems, high-risk candidates | Medium |
| `r/investing` | Value investing, long-term perspectives | Low |
| `r/smallstreetbets` | Lower-key WSB alternative | Medium |

**Scanning Method:**
1. Stream new submissions and comments via `subreddit.stream.submissions()` and `.comments()`
2. Extract ticker mentions via regex: `\$?[A-Z]{1,5}\b`
3. Filter out major indices (SPY, QQQ, DIA), mega-caps (AAPL, MSFT, NVDA), crypto (BTC, ETH)
4. Track per-ticker metrics:
   - Mention count (1h, 6h, 24h rolling windows)
   - Mention velocity (% change vs 7-day average)
   - Comment volume in ticker threads
   - Upvote ratio of ticker posts

**Sentiment:**
- Primary: VADER (vaderSentiment) — tuned for social media, handles caps, slang, emojis
- Optional upgrade: FinBERT via HuggingFace for finance-specific sentiment
- Output: score -1.0 (bearish) to +1.0 (bullish), aggregated per ticker

**Unusual Activity Triggers:**
```
- Mention velocity > 3x 7-day average
- Comment volume > 5x 7-day average
- Sentiment shift > 0.4 within 6 hours
```

### 2. SEC Filings Analyzer

**Library:** edgartools 4.6.3

**Filings Analyzed:**

| Filing | What It Reveals | Refresh Cadence |
|--------|-----------------|-----------------|
| 10-K (Annual) | Full financials, risk factors, business overview | Annual |
| 10-Q (Quarterly) | Quarterly trends, revenue/profit trajectory | Quarterly |
| 8-K (Material Events) | M&A, contracts, leadership changes | Real-time |
| Form 4 (Insider Trading) | C-suite and director buying/selling | Real-time |
| 13F (Institutional) | Fund holdings changes | Quarterly |

**Key Metrics Extracted:**

| Category | Metrics | Bullish Signal |
|----------|---------|----------------|
| Revenue Growth | YoY quarterly, 2-year trend | >20% YoY, accelerating |
| Profitability | Gross margin, operating margin | Expanding margins |
| Balance Sheet | Current ratio, debt/equity, cash | Cash > total debt |
| Insider Activity | Net buys vs sells (Form 4) | 2+ insiders buying with cash |
| Risk Factors | Disclosure changes | No new material risks |

### 3. News Sentiment

**Library:** finnhub-python 2.4.28

**Pipeline:**
1. Fetch latest news for tickers surfaced by Reddit or SEC scanner
2. Filter by relevance (headline or body contains ticker/company name)
3. FinBERT sentiment scoring per article (-1.0 to +1.0)
4. Aggregate: % bullish articles, % bearish, sentiment trend direction

**Upgrade Path:** Local FinBERT via HuggingFace transformers to eliminate API rate limits.

### 4. Technical Screen (Pre-Filter)

A lightweight technical filter applied before deep analysis:
- Price > $1 (exclude OTC/pink sheet risks)
- Price < 15-day SMA (bounce setup) OR Price > 20-day high (breakout setup)
- Volume > 50-day average (confirms real interest)
- Market cap $10M - $2B (small-cap inefficiency zone)
- RSI < 35 (oversold) OR RSI trending above 50 (momentum building)

---

## Gem Detector — Multi-Signal Confluence

The gem detector combines all signal sources into a single 0-100 score.

### Scoring Weights

| Source | Max Points | What Contributes |
|--------|-----------|------------------|
| Reddit | 25 | Mention velocity > 3x avg (15), positive sentiment > 0.6 (10) |
| SEC Fundamentals | 30 | Revenue growth > 20% (15), insider buying (10), cash > debt (5) |
| News Sentiment | 20 | FinBERT bullish > 0.7 aggregate score |
| Technical Setup | 25 | Clean pattern (15), volume confirmation (10) |

**Total: 100 points maximum**

### Alert Thresholds

| Score | Classification | Action |
|-------|---------------|--------|
| 80-100 | Strong Gem | Push notification + Telegram alert immediately |
| 65-79 | Potential Gem | Telegram alert only |
| 50-64 | Watchlist | Added to monitoring database, no alert |
| <50 | Discard | No action |

---

## Validation Layer (Before Alerting)

1. Ticker is still actively trading (not halted, not delisted)
2. Recent news is NOT pump-and-dump language patterns
3. Price hasn't already moved > 15% since signal generation (don't chase)
4. Market cap within target range ($10M - $2B)
5. At least **2 independent signal sources** must agree (cross-reference requirement)

---

## Telegram Alert Format

```
===== STRADEGY GEM ALERT =====
$PLUG — 3-signal confluence (score: 87/100)

Momentum: Breakout above 20-day high on 2.3x avg volume
Reddit: +340% mention surge, sentiment 0.78 bullish
Fundamentals: Q1 rev +32% YoY, P/S 0.8, $42M cash, $0 debt

Suggested Entry: $4.20 | Stop: $3.90 | Target: $5.10
Risk/Reward: 1:3 | Max Position: $9.00

SEC: https://www.sec.gov/...
Reddit: https://reddit.com/r/stocks/...
================================
```

## Schedule

| Time | Action |
|------|--------|
| Market Open (9:30 AM ET) | Full research pipeline scan |
| Every 15 min (trading hours) | Incremental Reddit + news scan |
| Market Close (4:00 PM ET) | SEC filings review, watchlist update |
| Weekend | Deep fundamental analysis on watchlist |

## Anti-Fabrication Controls

1. Every signal MUST have a source URL (Reddit link, SEC filing URL, news article URL)
2. LLMs (GPT/Claude) used ONLY for text summarization — never for buy/sell decisions
3. FinBERT provides sentiment scores only — one signal among many
4. Price targets and stops derive from ATR calculations, not LLM predictions
5. Cross-reference: a gem must have signals from 2+ independent sources
