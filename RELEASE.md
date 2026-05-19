# Stradegy v2.0.0 Release Notes

**Release Date:** May 18, 2026  
**Codename:** Autonomous VM  
**Live URL:** https://stradegy.duckdns.org

---

## 🎉 Major Highlights

### VM-First Deployment Architecture
Stradegy has been completely re-architected for VM deployment. The Docker-based NAS deployment has been replaced with a native Ubuntu VM deployment running Python 3.12 in a virtual environment, managed by systemd for automatic boot recovery. This resolves all prior Docker disk space, build timeout, and port conflict issues.

### Free Open-Source HTTPS
Full HTTPS encryption via Let's Encrypt certificates obtained through Caddy reverse proxy on `stradegy.duckdns.org`. No Cloudflare purchases, no commercial dependencies — entirely free and open-source.

### 209-Ticker Universe with ~1M OHLCV Rows
The data pipeline now supports 209 US equities with 20+ years of historical OHLCV data (~1M rows in SQLite). All tickers have been backfilled and enriched with real company names and sector classifications.

### Real-Time WebSocket Push Updates
All scheduled jobs now broadcast real-time updates via WebSocket:
- `portfolio_update` after daily data refresh
- `alerts_update` after every research scan
- `metrics_update` after self-improvement cycle

Frontend receives live push notifications without polling.

### Ticker Detail Views
Click any ticker card to see a dedicated detail page with a 90-day sparkline chart, company name, sector, and classification. The tickers page features real-time sparklines, sector filters, and search.

### Vault Secrets Management
API keys (Alpaca, Finnhub, Discord) can be configured directly through the Settings UI. Changes are written to `.env` with `chmod 600` permissions, providing a user-friendly secrets vault.

---

## 🚀 What's New

### Frontend Enhancements
- **Tickers Page**: 209 ticker cards with real names, sectors, sparkline charts, sector filters, and search
- **Ticker Detail Page**: `/tickers/:symbol` route with 90-day price history chart
- **Error Boundary**: React error boundary with friendly error UI and reload button
- **Pull-to-Refresh**: Touch gesture detection for mobile refresh
- **App Badge**: `navigator.setAppBadge()` for unread alerts on supported platforms
- **Offline Persistence**: TanStack Query cache persisted to localStorage
- **10s API Timeout**: All API calls use 10-second timeout (up from 3s)
- **Clean Error Handling**: Removed all silent `.catch(() => fallback)` patterns — errors are now visible
- **SPA Routing Fix**: Catch-all route serves `index.html` for React Router paths (`/alerts`, `/portfolio`, etc.)

### Backend Enhancements
- **Portfolio Metrics Endpoint**: `/api/portfolio/metrics` returns real performance metrics
- **Alerts Approve/Reject**: Full pre-trade safety checks (market hours, position limits, drawdown kill switch, order status polling)
- **Drawdown Color Logic**: Severe (-20%+) shows red, moderate (-10%) shows amber
- **Peak Equity Tracking**: Portfolio snapshots now track peak equity for accurate drawdown calculation
- **Order Status Polling**: AlpacaClient now polls `poll_order_fill` for order execution status
- **WebSocket Broadcasting**: `_research_scan_with_broadcast` wrapper broadcasts after every scheduled scan
- **API Timeout Increased**: 3s → 10s for all external API calls

### Infrastructure
- **VM Deployment**: Native Python venv on Ubuntu 22.04 VM (192.168.1.168)
- **Systemd Auto-Start**: `stradegy.service` enabled for boot resilience
- **Caddy Reverse Proxy**: Automatic HTTPS with Let's Encrypt, auto-renewal
- **Port 80/443 Isolation**: No conflict with UGreen NAS WebUI (NAS restored and running independently)
- **DuckDNS Integration**: `stradegy.duckdns.org` → public IP with active certificate

---

## 🔧 Fixes

### Critical Audit Fixes
1. **Duplicate RiskManager Methods**: Removed 104 lines of duplicate code
2. **Missing `get_latest_price`**: Added to DataStore for ticker detail view
3. **Drawdown Kill Switch**: Wired into `approve_alert` with peak_equity tracking
4. **Market Hours Gate**: Trading blocked outside Mon-Fri 9:30–16:00 ET
5. **Position Limit Gate**: Blocks trades exceeding tier max position count
6. **Order Status Polling**: Added `poll_order_fill` to AlpacaClient for fill confirmation

### UI Fixes
- **$0.00 Bug**: Portfolio now shows real $100,000.00 equity from Alpaca paper account
- **"Unknown" Tickers**: All 191 tickers now display real company names and sectors
- **"undefined" Price**: Fixed sparkline price display when data is undefined
- **Stale Build**: Frontend base path fixed from `/stradegy/` to `/` for VM root deployment
- **Loading States**: Proper loading indicators on all data-dependent components

---

## 🗑️ Removed

### Operational Scripts (One-Time Use)
The following scripts were used during initial setup and are no longer needed in the repository:
- `deploy.sh` — Docker deployment script
- `fix-and-deploy.sh` — NAS fix + deploy
- `fix-nas-ui.sh` — NAS WebUI recovery
- `fix-nas-ui-deep.sh` — NAS WebUI deep fix
- `setup-vm.sh` — VM setup script
- `remove-stradegy.sh` — Remove Stradegy from NAS
- `setup-cloudflare-tunnel.sh` — Cloudflare tunnel setup (not used)
- `cleanup-buildx.sh` — Docker build cache cleanup
- `cleanup-docker.sh` — Docker space cleanup

### Docker Artifacts
- `Dockerfile` — Not used in native deployment
- `docker-compose.yml` — Not used (was for NAS Docker deployment)
- `docker-compose.vm.yml` — Not used (was for VM Docker deployment)

### CI/CD
- `.github/workflows/build-and-deploy.yml` — Obsolete GHCR workflow

### Temporary Files
- `UAT_REPORT_2026-05-18.md` — Completed UAT report
- `NEXT_SESSION.md` — Session handoff document
- Screenshot files (`01-homepage-desktop.png` through `10-settings-mobile.png`)

---

## 📊 Repository Cleanup

**Before:** 45 tracked files including operational scripts, Docker configs, screenshots, and temporary reports.  
**After:** 18 tracked files — clean, focused repository containing only application code, configuration, and documentation.

---

## 🔐 Security

- All API keys sourced from `backend/.env` with `chmod 600`
- Vault secrets UI writes to `.env` with restricted permissions
- No secrets in git (all credential files in `.gitignore`)
- Paper trading by default (`PAPER_TRADING=true`)
- Kill switch at 20% drawdown from peak
- PDT guard for sub-$25k accounts

---

## 🧪 Verification

All changes verified by independent agents:
- **UAT Audit**: Full user acceptance testing of PWA functionality
- **Frontend RCA**: Root cause analysis of all UI issues
- **Backend API Investigation**: Verification of all API endpoints
- **Gap Analysis Audit**: Comprehensive feature completeness review

---

## 📚 Documentation

- Updated `README.md` with current VM deployment instructions
- `plans/DEPLOYMENT.md` reflects native deployment (not Docker)
- `plans/ARCHITECTURE.md` updated for VM architecture
- All version references bumped to v2.0.0

---

## 🎯 What's Next

- Live trading graduation checklist at `plans/LIVE_TRADING_CHECKLIST.md`
- 4+ weeks of paper trading validation
- First self-improvement cycle run (scheduled Sundays at 02:00 UTC)
- PWA home screen installation on mobile devices

---

*Stradegy v2.0.0 — Clean, autonomous, and running on your own hardware.*
