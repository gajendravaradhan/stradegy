# Stradegy v3.0.0 Release Notes

**Release Date:** May 23, 2026
**Codename:** Daily Swipe
**Live URL:** https://stradegy.duckdns.org

---

## Major Highlights

### Left/Right Swipe Navigation (PWA)
The mobile PWA now supports natural left/right swipe gestures to navigate between tabs. Swipe left to go to the next tab, swipe right to go back — just like native iOS/Android apps. Smart gesture detection avoids conflicts with vertically scrolling lists, sparkline charts, and horizontally scrollable containers.

### Daily Self-Improvement Cycle
The self-improvement algorithm now runs **every day at 02:00 UTC** (overnight) instead of once per week. This enables the system to react faster to changing market conditions, adjust strategy weights more responsively, and continuously optimize based on the most recent trade traces.

### New Backend Modules
- **Alert System** (`engine/alerts/`): WhatsApp and multi-channel alert management
- **Monitoring Suite** (`engine/monitoring/`): Price monitor, risk monitor, correlation monitor, and data quality auditor
- **Overnight Backtesting** (`engine/backtest/overnight_backtest.py`): Nightly backtest runner for continuous strategy validation
- **Pre-Market Scanner** (`engine/research/premarket_scan.py`): Early morning research scan before market open
- **Social Stream & Trend Scanners**: Additional signal sources for the research pipeline

### Enhanced Research Pipeline
- Expanded Discord scanner with richer mention tracking
- Improved gem detector with better scoring and classification
- New SEC analyzer enhancements for insider transaction detection
- Reddit scanner optimizations for sentiment extraction

### Frontend Enhancements
- **Watchlist Page**: Dedicated page for tracking watched tickers
- **Interactive Sparklines**: Touch-friendly price charts with hover tooltips on ticker detail
- **Portfolio Improvements**: Better metrics display and trade history
- **Alerts Page**: Richer gem cards with signal breakdown
- **Settings Updates**: Additional configuration options

### Deployment & Infrastructure
- NAS deployment support with Caddy reverse proxy
- Docker Compose configurations for multiple deployment targets
- Health monitoring and log rotation scripts
- DuckDNS auto-update integration

---

## Breaking Changes

None. All changes are additive or configuration-level.

---

## Migration Guide

No migration needed. Update to v3.0.0 is a simple `git pull` and restart.

---

## What's Next

- Live trading graduation checklist at `plans/LIVE_TRADING_CHECKLIST.md`
- PWA home screen installation on mobile devices
- First daily self-improvement cycle run (tonight at 02:00 UTC)

---

*Stradegy v3.0.0 — Swipe, trade, improve. Daily.*
