# PWA UI Specification — Mobile-First Design

## Overview

The Stradegy PWA is a React application optimized for mobile phones, installed via
"Add to Home Screen". It uses a 5-tab bottom navigation pattern matching native
iOS/Android conventions. Default theme is dark (trading apps look wrong in light mode).

## Tech Stack (Frontend)

| Layer | Choice | Version |
|-------|--------|---------|
| Framework | React | 18.3.x |
| Build Tool | Vite | 6.x |
| Language | TypeScript | 5.7+ |
| Styling | Tailwind CSS | 3.4.x |
| Components | shadcn/ui | latest |
| Charts | Tremor (recharts) | 3.18.x |
| Data Fetching | TanStack Query | 5.x |
| State | Zustand | 5.x |
| Routing | React Router | 7.x |
| Icons | Lucide React | latest |
| PWA | vite-plugin-pwa | 0.21.x |

---

## Navigation Structure

### Bottom Tab Bar (5 Tabs)

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│   Home   │  Alerts  │Portfolio │Strategies│ Settings │
│ (Layout  │(Sparkles)│(Briefcase│(Trending │(Settings)│
│Dashboard)│          │Business) │    Up)   │          │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Screen 1: Dashboard (Home)

### Purpose
At-a-glance view of account health, performance, and equity curve.

### Layout
```
┌──────────────────────────────┐
│  Stradegy            🔔  ⚡  │  Top bar: app name, alerts badge, paper/live indicator
├──────────────────────────────┤
│  Total Equity                │
│  $247.83         +$12.34 ↗  │  Large display, green/red daily change
├──────────────────────────────┤
│  ┌─────────┬─────────┬─────┐ │
│  │ Buying  │ Tax     │ Day │ │
│  │ Power   │ Reserve │ P&L │ │  Stat cards row (3 across)
│  │ $218.50 │ $29.33  │+$12 │ │
│  └─────────┴─────────┴─────┘ │
├──────────────────────────────┤
│  Equity Curve          [1M]  │
│  ┌────────────────────────┐  │
│  │     📈 line chart       │  │  Tremor AreaChart, touch-draggable
│  │    /\/\/\/\/\/\/\/\     │  │
│  └────────────────────────┘  │
├──────────────────────────────┤
│  Open Positions (2)          │
│  ┌────────────────────────┐  │
│  │ $PLUG  12 shares +$2.40│  │  Tap to expand, swipe to close
│  │ ████████░░░░ +3.2%    │  │
│  │ $RGTI  8 shares -$1.20 │  │
│  └────────────────────────┘  │
├──────────────────────────────┤
│  Recent Activity             │
│  • Bought 12 PLUG @ $4.20   │
│  • Sold 5 SOUN @ $3.80 (+$2)│
│  • New gem: $RGTI (score 82)│
└──────────────────────────────┘
```

### Components
- `EquityCard`: Large equity display with daily change
- `StatCard`: Grid of 3 metric cards (Buying Power, Tax Reserve, Day P&L)
- `EquityChart`: Interactive Tremor AreaChart with period selector (1W/1M/3M/6M/YTD)
- `PositionCardList`: Scrolling list of open position cards
- `ActivityFeed`: Reverse-chronological recent actions
- `PaperLiveBadge`: Indicates paper or live trading mode in top bar

### WebSocket Updates
- Real-time position P&L updates when market is open
- Alerts badge count increments live

---

## Screen 2: Alerts (Gem Discovery)

### Purpose
Browse, filter, and act on "hidden gem" discoveries.

### Layout
```
┌──────────────────────────────┐
│  Hidden Gems         🔍 ⚙    │  Search + filter
├──────────────────────────────┤
│  ┌──────┬──────┬──────────┐  │
│  │ All  │ Reddit│ SEC/News │  │  Filter chips (horizontal scroll)
│  └──────┴──────┴──────────┘  │
├──────────────────────────────┤
│  ┌────────────────────────┐  │
│  │ 🔥 $PLUG  Score: 87    │  │
│  │ Momentum breakout on    │  │
│  │ 2.3x volume + Reddit   │  │
│  │ buzz +14% mentions     │  │
│  │                         │  │
│  │ 📈 📊 📰 🔴             │  │  Signal type badges
│  │ Entry: $4.20  Stop: $3.90  │
│  │ Target: $5.10  R:R 1:3 │  │
│  │                         │  │
│  │ [Details]    [Trade →] │  │  In semi-auto: [Approve] [Reject]
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ $RGTI  Score: 82       │  │
│  │ Mean-reversion...      │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ $SOUN  Score: 76       │  │
│  │ ...                    │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

### Components
- `GemCard`: Card with ticker, score, signal summary, entry/stop/target, actions
- `SignalBadge`: Small indicator for each signal type (momentum, technical, Reddit, etc.)
- `FilterChips`: Horizontal scrollable filter buttons
- `GemDetailSheet`: Bottom sheet with full signal breakdown, SEC links, Reddit links

### Semi-Auto vs Full-Auto Behavior

| Mode | GemCard Actions |
|------|-----------------|
| Semi-Auto | `[Details] [Approve ✓] [Reject ✗]` |
| Full-Auto | `[Details]` (bot trades automatically, no approval needed) |

---

## Screen 3: Portfolio (Positions & History)

### Purpose
View current positions, trade history, tax status, and performance metrics.

### Layout
```
┌──────────────────────────────┐
│  Portfolio                   │
├──────────────────────────────┤
│  ┌──────────┬──────────────┐ │
│  │ Positions│ Trade History│ │  Segment toggle
│  └──────────┴──────────────┘ │
├──────────────────────────────┤
│  Current Positions (2)       │
│  ┌────────────────────────┐  │
│  │ PLUG  12 @ $4.20       │  │
│  │ Current: $4.40          │  │
│  │ P&L: +$2.40 (+4.8%)   │  │  Green = profit, red = loss
│  │ Opened: Mon 10:32 AM    │  │
│  │ Stop: $3.90 Tgt: $5.10 │  │
│  │              [Close →] │  │  Manual close button
│  └────────────────────────┘  │
├──────────────────────────────┤
│  Performance                 │
│  ┌───────┬───────┬────────┐  │
│  │WinRate│Sharpe │ProfitF │  │
│  │  62%  │ 1.2   │  1.8   │  │
│  └───────┴───────┴────────┘  │
│  Avg Win +$3.20 | Avg Loss -$1.80
├──────────────────────────────┤
│  Tax Summary                 │
│  Realized Gains: $48.50      │
│  Tax Reserve: $14.55 (30%)   │
│  Available: $203.28          │
└──────────────────────────────┘
```

### Components
- `SegmentToggle`: Switches between "Positions" and "Trade History"
- `PositionCard`: Swipeable card with P&L bar, stop/target, close button
- `TradeHistoryList`: Chronological list of closed trades with P&L
- `PerformanceGrid`: Metrics in a compact grid
- `TaxSummary`: Tax reserve breakdown with visual indicator

---

## Screen 4: Strategies (Engine Room)

### Purpose
Monitor and control active strategies, view backtest results, track self-improvement.

### Layout
```
┌──────────────────────────────┐
│  Strategy Engine             │
├──────────────────────────────┤
│  Tier: Micro ($247)          │
│  Max Positions: 1 | Risk: 3% │
├──────────────────────────────┤
│  Active Strategies           │
│  ┌────────────────────────┐  │
│  │ Mean Reversion   [ON]  │  │  Toggle switch
│  │ Weight: 65%  Sharpe: 1.4│  │
│  │ 7-day P&L: +$8.20      │  │
│  │ Version: v3 (active)   │  │
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ Momentum Breakout [ON] │  │
│  │ Weight: 35%  Sharpe: 0.9│  │
│  │ 7-day P&L: +$3.40      │  │
│  │ Version: v2 (active)   │  │
│  └────────────────────────┘  │
├──────────────────────────────┤
│  Backtest Summary            │
│  ┌────────────────────────┐  │
│  │ Walk-Forward (2023-24) │  │  Tap to expand
│  │ Sharpe 1.3 Max DD -12% │  │
│  └────────────────────────┘  │
├──────────────────────────────┤
│  Self-Improvement            │
│  ┌────────────────────────┐  │
│  │ Last cycle: Sat 8pm    │  │
│  │ 2 skills adopted        │  │
│  │ Win rate: 61% → 68% ▲  │  │
│  │ [View Details]         │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

### Components
- `CapitalTierBadge`: Shows current tier with key limits
- `StrategyCard`: Toggle + allocation + 7-day P&L + version info
- `BacktestSummary`: Collapsible card with key metrics
- `SelfImprovementCard`: Last cycle results, improvements adopted

---

## Screen 5: Settings (Configuration)

### Purpose
Configure API keys, risk parameters, autonomy mode, notifications, and tax rates.

### Layout
```
┌──────────────────────────────┐
│  Settings                    │
├──────────────────────────────┤
│  Trading Mode                │
│  ┌──────────────────────────┐│
│  │ ○ Paper Trading          ││
│  │ ● Live (Alpaca)          ││  Radio group
│  └──────────────────────────┘│
├──────────────────────────────┤
│  Autonomy Mode               │
│  ┌──────────────────────────┐│
│  │ ● Semi-Autonomous        ││
│  │   Bot suggests, you      ││
│  │   approve/reject trades  ││
│  │ ○ Full-Autonomous        ││
│  │   Bot trades autonomously││
│  └──────────────────────────┘│
├──────────────────────────────┤
│  API Configuration           │
│  Alpaca Key     ••••••••    │  Masked, tap to edit
│  Alpaca Secret  ••••••••    │
│  Telegram Token ••••••••    │
│  Finnhub Key    ••••••••    │
│  Reddit Client  ••••••••    │
├──────────────────────────────┤
│  Risk Parameters             │
│  Max Drawdown      20%       │  Editable values
│  Risk Per Trade     3%       │
│  Max Positions      1        │
│  Stop ATR Mult.    1.5x      │
├──────────────────────────────┤
│  Tax Settings                │
│  Short-Term Rate    30%      │
│  Long-Term Rate     15%      │
├──────────────────────────────┤
│  Notifications               │
│  Telegram Gems     [ON]      │  Toggle switches
│  Telegram P&L      [ON]      │
│  Push Notify       [ON]      │
│  Trade Executed    [ON]      │
├──────────────────────────────┤
│  About                       │
│  Version 1.0.0  Build 42    │
│  [View Logs] [Export Data]   │
└──────────────────────────────┘
```

---

## PWA-Specific Features

| Feature | Implementation |
|---------|---------------|
| **Installable** | Web App Manifest with `display: standalone`, custom icons (192px + 512px), splash screen |
| **Offline Support** | Service worker caches static assets + API responses via TanStack Query persistence |
| **Push Notifications** | Web Push API via service worker. Gem alerts delivered when app is closed |
| **Dark Theme Only** | `prefers-color-scheme: dark` enforced. No light mode toggle needed |
| **Safe Area Insets** | CSS `env(safe-area-inset-bottom)` for iPhone notch/dynamic island |
| **Splash Screen** | Solid dark background with app logo (defined in manifest) |
| **Pull to Refresh** | Gesture-based refresh on scrollable list screens |
| **App Badge** | `navigator.setAppBadge(count)` for unread gem alerts |

### manifest.json Example

```json
{
  "name": "Stradegy",
  "short_name": "Stradegy",
  "description": "Autonomous trading bot — research, backtest, trade, improve",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "theme_color": "#09090b",
  "background_color": "#09090b",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

---

## Design System

### Colors (Dark Theme — Tailwind Zinc/Slate)

| Token | Color | Usage |
|-------|-------|-------|
| Background | `zinc-950` (#09090b) | Main screen background |
| Surface | `zinc-900` (#18181b) | Cards, sheets |
| Surface Elevated | `zinc-800` (#27272a) | Tappable cards, inputs |
| Text Primary | `zinc-100` (#f4f4f5) | Headings, values |
| Text Secondary | `zinc-400` (#a1a1aa) | Labels, metadata |
| Accent | `emerald-500` (#10b981) | Profits, buy, bullish |
| Danger | `red-500` (#ef4444) | Losses, sell, bearish |
| Warning | `amber-500` (#f59e0b) | Alerts, caution |

### Typography
- **Headings:** Inter, 16-24px, semibold
- **Body:** Inter, 14px, regular
- **Values (monetary):** JetBrains Mono, 16-24px, medium (tabular numbers)
- **Small text:** Inter, 12px, regular

### Spacing
- 16px base grid
- Cards: 16px padding, 8px border-radius, 1px border
- Tab bar: 56px height, safe area inset bottom

---

## Component States

All interactive components must handle:

| State | Behavior |
|-------|----------|
| **Loading** | Skeleton placeholders (shimmer animation) |
| **Empty** | Illustration + message (e.g., "No open positions") |
| **Error** | Retry button + error message |
| **Offline** | Stale data badge + "Offline" indicator |
| **Success** | Normal data display |
| **Disabled** | Reduced opacity, non-interactive |

---

## Accessibility

- All interactive elements have minimum 44x44px touch targets (iOS HIG / Android Material)
- Sufficient color contrast (WCAG AA minimum)
- Not purely color-based indicators (shapes + text alongside green/red)
- Screen reader labels on all interactive elements
