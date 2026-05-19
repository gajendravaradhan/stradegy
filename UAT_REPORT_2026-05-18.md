# Stradegy Trading Bot PWA — User Acceptance Test Report

**Test Date:** 2026-05-18  
**Tester:** QA Automation (Playwright)  
**Frontend URL:** https://gajendravaradhan.github.io/stradegy  
**Backend URL:** https://stradegy.duckdns.org  
**Browser:** Chromium (Playwright)  
**Viewports Tested:** 1280×720 (desktop), 375×812 (iPhone X mobile)

---

## Executive Summary

The Stradegy PWA is **non-functional in production**. The backend at `stradegy.duckdns.org` is completely unreachable, and the frontend deployed to GitHub Pages is a **stale build** that is missing major features present in the source code (Tickers page, Vault Secrets). Every API call returns 404, causing all financial data, alerts, and dynamic content to display zeros, empty states, or "undefined." The app renders as a static shell with no live data.

**Critical Issues:** 3  
**High Issues:** 4  
**Medium Issues:** 3  
**Low Issues:** 2  

---

## Issue #1 — CRITICAL: Backend Completely Down

- **Severity:** Critical
- **Area:** Infrastructure / Deployment
- **What I expected:** The backend API at `https://stradegy.duckdns.org` to respond to health checks and API requests.
- **What actually happened:** `net::ERR_CONNECTION_TIMED_OUT` on every request to `stradegy.duckdns.org`. The server is entirely unreachable.
- **Steps to reproduce:**
  1. Navigate to `https://stradegy.duckdns.org` → timeout.
  2. Navigate to `https://stradegy.duckdns.org/api/health` → timeout.
  3. Navigate to `http://stradegy.duckdns.org` → timeout.
- **Impact:** The entire trading bot is offline. No data, no alerts, no order execution, no portfolio sync.
- **Screenshot:** N/A (connection timeout, blank page)

---

## Issue #2 — CRITICAL: Frontend Has No Backend Connectivity

- **Severity:** Critical
- **Area:** API / Configuration
- **What I expected:** The frontend to call the backend API at `stradegy.duckdns.org` or have a configurable API base URL.
- **What actually happened:** The frontend makes all API calls to relative paths (`/api/...`), which resolve to `https://gajendravaradhan.github.io/api/...` on GitHub Pages. Every endpoint returns HTTP 404.
- **Console errors observed:**
  - `Failed to load resource: the server responded with a status of 404` for:
    - `/api/portfolio`
    - `/api/data/tickers/AAPL/sparkline?days=90`
    - `/api/alerts?min_score=50&limit=20`
    - `/api/strategies`
    - `/api/settings`
    - `/api/portfolio/history?days=90`
    - `/api/portfolio/metrics?days=90`
- **Steps to reproduce:**
  1. Open https://gajendravaradhan.github.io/stradegy
  2. Open browser DevTools → Network tab
  3. Observe all `/api/*` requests returning 404
- **Impact:** All screens show empty fallback data ($0.00, 0 positions, no gems, no charts).
- **Screenshot:** `01-homepage-desktop.png`, console logs attached.

---

## Issue #3 — CRITICAL: Deployed Build Is Stale / Missing Major Features

- **Severity:** Critical
- **Area:** Build / CI-CD / Deployment
- **What I expected:** The deployed frontend on GitHub Pages to match the current source code in the repository.
- **What actually happened:** The deployed JS bundle (`assets/index-ViQKvp7M.js`) does **not** contain the string "Tickers" or "Vault Secrets", confirming the build is significantly older than the source code.
- **Missing in deployed build:**
  1. **Tickers page** — Source has `src/pages/Tickers.tsx` and a `/tickers` route with a search bar, sector filters, and mini sparklines. The deployed app has only 5 nav buttons (missing Tickers).
  2. **Vault Secrets section in Settings** — Source has a full `VaultSecretsSection` component with 6 masked input fields (Alpaca API Key, Alpaca Secret, Finnhub API Key, Discord Bot Token, etc.) and an Eye/EyeOff toggle. The deployed Settings page only shows Trading Mode, Autonomy Mode, Risk Parameters, and Tax Settings.
- **Verification:**
  - DOM query `document.querySelectorAll('nav button').length` returns **5** (should be 6).
  - JS bundle grep for "Tickers" and "Vault Secrets" returns **0 matches**.
- **Impact:** Users cannot configure API secrets in the UI. The Tickers page is entirely inaccessible.
- **Screenshot:** `05-settings-page.png` (no secrets section), `10-settings-mobile.png`

---

## Issue #4 — HIGH: All Financial Data Shows $0.00 / Empty Fallbacks

- **Severity:** High
- **Area:** Dashboard / Portfolio
- **What I expected:** Real portfolio equity, buying power, tax reserve, and position data from Alpaca.
- **What actually happened:** Because the backend is unreachable, the frontend falls back to hardcoded zero values:
  - Portfolio Value: **$0.00**
  - Buying Power: **$0.00**
  - Tax Reserve: **$0.00**
  - Positions: **0**
  - Day P&L: **+$0.00 (0.00%)**
  - Open Positions list: "No open positions"
  - Recent Activity: "No recent activity"
  - Portfolio chart: Not rendered (history array is empty)
- **Steps to reproduce:**
  1. Open the homepage.
  2. Observe all stat cards showing $0.00.
- **Impact:** The dashboard is useless without a running backend. Users cannot see any real trading data.
- **Screenshot:** `01-homepage-desktop.png`, `06-homepage-mobile.png`

---

## Issue #5 — HIGH: AAPL Trend Shows "$undefined"

- **Severity:** High
- **Area:** Dashboard / Data Display
- **What I expected:** The selected ticker trend card to show the current price or a graceful "—" placeholder when data is unavailable.
- **What actually happened:** The price label reads **"$undefined"** because `sparklineData[sparklineData.length - 1]?.close` is `undefined` when the API fails, and string interpolation produces "$undefined".
- **Code location:** `frontend/src/pages/Dashboard.tsx:176`
- **Steps to reproduce:**
  1. Open the homepage with the backend down.
  2. Look at the "AAPL Trend" card.
- **Impact:** Looks broken and unprofessional. Indicates poor null-safety.
- **Screenshot:** `01-homepage-desktop.png` (top right of dashboard)

---

## Issue #6 — HIGH: Alerts/Gems Page Empty — Cannot Test Approval Flow

- **Severity:** High
- **Area:** Alerts / Trade Execution
- **What I expected:** A list of "Hidden Gems" with scores, source breakdowns, and Approve/Reject buttons. In semi-autonomous mode, approving should trigger an order.
- **What actually happened:** The page displays "No gems discovered yet" with a decorative icon because the `/api/alerts` endpoint returns 404 and the fallback is an empty array.
- **Steps to reproduce:**
  1. Navigate to the Alerts/Gems page (second nav button on desktop, or direct `#/alerts`).
  2. Observe empty state message.
- **Impact:** The core semi-autonomous trading workflow (approve/reject gems) is completely untestable in production. There is no evidence that order execution works.
- **Screenshot:** `02-alerts-page.png`, `07-alerts-mobile.png`

---

## Issue #7 — HIGH: No Ticker Detail View Exists

- **Severity:** High
- **Area:** Tickers / Navigation
- **What I expected:** Clicking a ticker card on the Tickers page (or the AAPL trend card) should navigate to a detail view with a full chart, fundamentals, and signal history.
- **What actually happened:** There is **no ticker detail route** in `App.tsx` and no click handler on ticker cards in `Tickers.tsx`. The cards are purely presentational.
- **Code evidence:** `App.tsx` routes: `/`, `/tickers`, `/alerts`, `/portfolio`, `/strategies`, `/settings`. No `/tickers/:symbol` route. `Tickers.tsx` line 99–121 has no `onClick` handler.
- **Impact:** Users cannot drill down into individual stocks. The app is missing a fundamental navigation pattern for a trading tool.
- **Screenshot:** N/A (feature absent)

---

## Issue #8 — MEDIUM: Settings Page Missing Secrets Configuration

- **Severity:** Medium
- **Area:** Settings / UX
- **What I expected:** A "Vault Secrets" section with masked input fields for Alpaca API Key, Alpaca Secret Key, Finnhub API Key, Discord Bot Token, etc., plus a Save button.
- **What actually happened:** The deployed Settings page has **no secrets section at all**. The source code includes it, but the stale build omits it. Even if the build were current, the API calls to `/api/secrets` would 404 because the backend is down.
- **Steps to reproduce:**
  1. Navigate to Settings.
  2. Scroll through all sections.
  3. Observe no API key inputs.
- **Impact:** Users cannot configure the bot via the UI. They must manually edit `.env` files or backend config.
- **Screenshot:** `05-settings-page.png`, `10-settings-mobile.png`

---

## Issue #9 — MEDIUM: PWA Manifest & Icon Warnings

- **Severity:** Medium
- **Area:** PWA / Installability
- **What I expected:** Clean manifest, valid icons, no console warnings.
- **What actually happened:**
  - **Warning:** `Manifest: property 'scope' ignored. Start url should be within scope of scope URL.`
  - **Warning:** `<meta name="apple-mobile-web-app-capable" content="yes"> is deprecated. Please include <meta name="mobile-web-app-capable" content="yes">`
  - **404 Error:** `https://gajendravaradhan.github.io/icons/icon-192.png.svg` (the manifest references `icon-192.png.svg` which does not exist; the file is likely `icon-192.png`)
- **Steps to reproduce:**
  1. Open the app.
  2. Open DevTools → Console.
  3. Observe warnings on load.
- **Impact:** PWA installability may be degraded on some browsers. The icon download error could prevent the install prompt from appearing.
- **Screenshot:** Console logs attached.

---

## Issue #10 — MEDIUM: Micro Tier Badge Is Not Interactive

- **Severity:** Medium
- **Area:** Portfolio / UX
- **What I expected:** The "Micro" tier badge on the Portfolio page to be clickable, showing tier details or an upgrade path.
- **What actually happened:** The tier badge is a **static display element** with no `onClick` handler. It shows the current tier name (e.g., "Micro") and a description, but tapping it does nothing.
- **Code evidence:** `Portfolio.tsx` lines 41–46 render the badge as a `<div>`, not a `<button>`.
- **Steps to reproduce:**
  1. Go to Portfolio page.
  2. Click the "Micro" tier badge next to Total Equity.
  3. Nothing happens.
- **Impact:** Users cannot view tier thresholds or understand how to graduate to "Small" or "Standard" tiers from the UI.
- **Screenshot:** `03-portfolio-page.png`, `08-portfolio-mobile.png`

---

## Issue #11 — LOW: App Version Mismatch

- **Severity:** Low
- **Area:** Branding / QA
- **What I expected:** The version displayed in Settings to match the README and package.json.
- **What actually happened:**
  - README says: `Stradegy v1.0.0`
  - `package.json` says: `version: "0.1.0"`
  - Settings footer says: `Stradegy v0.1.0`
- **Impact:** Minor inconsistency, but confusing for users checking which version they are running.

---

## Issue #12 — LOW: Bottom Navigation Labels Hidden on Desktop

- **Severity:** Low
- **Area:** Navigation / Accessibility
- **What I expected:** Bottom nav to show icon + label, or at least have accessible `aria-label` attributes.
- **What actually happened:** The `TabBar` component renders only icons (no text labels) and no `aria-label` on the buttons. On desktop, users must hover or guess what each icon means.
- **Code evidence:** `TabBar.tsx` renders `<Icon size={20} ... />` with no accompanying text or aria attributes.
- **Impact:** Poor accessibility and slightly confusing UX for new users on larger screens.
- **Screenshot:** All page screenshots show icon-only nav.

---

## Mobile Responsiveness Assessment

| Page | Mobile Layout | Usability | Notes |
|------|---------------|-----------|-------|
| Dashboard | ✅ Pass | ⚠️ Marginal | Content fits, but all $0.00 makes it useless. Bottom nav safe-area padding works. |
| Alerts | ✅ Pass | ⚠️ Marginal | Empty state centered and readable. No gems to test scrolling. |
| Portfolio | ✅ Pass | ⚠️ Marginal | Metrics grid (2 columns) fits. Tabs work. No positions to test card layout. |
| Strategies | ✅ Pass | ✅ Good | Sliders are touch-friendly. Deactivate buttons accessible. |
| Settings | ✅ Pass | ⚠️ Marginal | Radio groups stack well. Missing secrets section makes it incomplete. |

**Overall:** The layout framework is mobile-first and works correctly at 375px width. The primary failure is **missing data and missing features**, not broken CSS.

---

## Screenshots Captured

| File | Description |
|------|-------------|
| `01-homepage-desktop.png` | Dashboard at 1280×720 — shows $0.00 across the board, "No chart data", "$undefined" on AAPL trend |
| `02-alerts-page.png` | Alerts page — "No gems discovered yet" empty state |
| `03-portfolio-page.png` | Portfolio page — $0.00 equity, 0 positions, Micro tier badge, metrics grid with dashes |
| `04-strategies-page.png` | Strategies page — 3 strategies with sliders, all P&L at $0.00 |
| `05-settings-page.png` | Settings page — Paper/Live mode, Semi/Full autonomy, risk params, tax settings. **NO secrets section.** |
| `06-homepage-mobile.png` | Dashboard at 375×812 — same empty data, safe-area padding visible |
| `07-alerts-mobile.png` | Alerts at 375×812 — empty state centered |
| `08-portfolio-mobile.png` | Portfolio at 375×812 — metrics grid, empty positions state |
| `09-strategies-mobile.png` | Strategies at 375×812 — sliders usable, touch-friendly |
| `10-settings-mobile.png` | Settings at 375×812 — radio buttons stacked, version footer visible |

---

## Recommendations (Priority Order)

1. **Restore the backend** — `stradegy.duckdns.org` must be online. Verify DNS, server status, and SSL certificate.
2. **Fix API base URL** — The frontend should call the backend domain explicitly (e.g., `https://stradegy.duckdns.org/api`) rather than relative paths, or use a proxy/environment variable.
3. **Redeploy the frontend** — The GitHub Pages build is stale. Trigger a fresh build + deploy from the latest `main` branch so the Tickers page and Vault Secrets section appear.
4. **Fix "$undefined" bug** — Add null-safety to the sparkline price display in `Dashboard.tsx`.
5. **Add ticker detail view** — Create a `/tickers/:symbol` route with a detailed chart, stats, and signal history.
6. **Fix PWA manifest & icons** — Correct the icon path in the manifest (remove `.svg` suffix if the file is `.png`), add `mobile-web-app-capable` meta tag, and fix scope/start_url.
7. **Make tier badge interactive** — Add a modal or tooltip showing tier thresholds and graduation requirements.
8. **Add nav labels or aria-labels** — Improve accessibility of the bottom tab bar.

---

## Test Environment Log

```
Playwright Chromium
Desktop: 1280×720
Mobile: 375×812 (iPhone X)
Hash router used: Yes
Service Worker registered: Yes (vite-plugin-pwa)
Console errors (unique): 
  - /api/portfolio 404
  - /api/data/tickers/AAPL/sparkline?days=90 404
  - /api/alerts?min_score=50&limit=20 404
  - /api/strategies 404
  - /api/settings 404
  - /icons/icon-192.png.svg 404
Console warnings (unique):
  - Manifest scope ignored
  - apple-mobile-web-app-capable deprecated
```

---

*End of Report*
