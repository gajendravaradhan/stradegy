# Live Trading Graduation Checklist — Phase 13

## Pre-Requisites
- [ ] 4+ weeks of successful paper trading completed
- [ ] Paper trading results documented and compared to backtest expectations
- [ ] Backtest Sharpe ratio > 0.5 and max drawdown < 20%
- [ ] Self-improvement cycle has run at least once and improved a baseline
- [ ] All 53 unit/integration tests passing
- [ ] Docker image builds successfully
- [ ] PWA installs and loads on phone via HTTPS

## Account Setup
- [ ] Alpaca live account funded with $200 minimum
- [ ] API keys generated and stored in `.env` (never committed)
- [ ] Paper trading mode disabled (`PAPER_TRADING=false` in `.env`)
- [ ] Alpaca account status verified as "ACTIVE"

## Risk Configuration
- [ ] Max drawdown limit reviewed and set (default: 20%)
- [ ] Risk per trade reviewed (default: 3%)
- [ ] Max positions appropriate for account size (default: 1)
- [ ] ATR stop multiplier confirmed (default: 1.5x)
- [ ] Tax reserve rate set for jurisdiction (default: 30% short-term)

## Pre-Launch Verification
- [ ] `/api/portfolio` returns live Alpaca equity and positions
- [ ] `/api/settings` confirms `paper_trading: false`
- [ ] Telegram bot is configured and sends test message
- [ ] Research pipeline jobs scheduled and running
- [ ] Daily data refresh scheduled and working
- [ ] Self-improvement weekly cron scheduled

## Launch Day
- [ ] Deploy updated Docker container to NAS
- [ ] Verify Cloudflare Tunnel is serving HTTPS
- [ ] Open PWA on phone, confirm connectivity
- [ ] Monitor first trade execution via Telegram alert
- [ ] Confirm position appears in Portfolio page

## Post-Launch Monitoring
- [ ] Review daily P&L report each evening
- [ ] Check drawdown status weekly
- [ ] Run first self-improvement cycle on live data (after 1 week)
- [ ] Compare live results to backtest projections monthly
- [ ] Scale up capital only after 3 months of consistent profitability

## Emergency Procedures
- [ ] Know how to halt trading instantly (set `AUTONOMY_MODE=semi` or stop container)
- [ ] Have Alpaca dashboard bookmarked for manual intervention
- [ ] Document kill switch trigger levels

---

**Target Account Size Progression**

| Phase | Capital | Strategy |
|-------|---------|----------|
| 1 | $200 | Micro — 1 position, 3% risk |
| 2 | $2,500 | Small — 2-3 positions |
| 3 | $25,000 | Standard — full diversification |

Move to the next phase only after the current phase shows 2+ months of profitable, stable performance with drawdowns under the limit.
