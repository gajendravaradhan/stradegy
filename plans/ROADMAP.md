# Roadmap — Build Phases

## Phase Sequence

Each phase builds on the previous. Phases 1-8 are internal validation.
Phase 9 is paper trading. Phase 13 is live with real money.

```
Phase 1 ──▶ 2 ──▶ 3 ──▶ 4 ──▶ 5 ──▶ 6 ──▶ 7 ──▶ 8 ──▶ 9 ──▶ 10 ──▶ 11 ──▶ 12 ──▶ 13
Foundation  Data  Research  TG  Strats  Backtest  Risk  Alpaca  Self-Imp  API  PWA  Deploy  LIVE
```

---

## Phase 1: Foundation
| Task | Description |
|------|-------------|
| 1.1 | Initialize monorepo with `backend/` and `frontend/` directories |
| 1.2 | Create `pyproject.toml` with Python dependencies |
| 1.3 | Create `package.json` with React/TypeScript dependencies |
| 1.4 | Set up `Dockerfile` and `docker-compose.yml` |
| 1.5 | Create `.gitignore`, `.env.example` |
| 1.6 | Create `plans/` documentation folder |
| **Deliverable** | Project scaffold that runs `docker compose up` successfully |

## Phase 2: Data Pipeline
| Task | Description |
|------|-------------|
| 2.1 | Implement yfinance EOD downloader |
| 2.2 | Set up SQLite schema (OHLCV, tickers, market_data) |
| 2.3 | Implement data store with caching |
| 2.4 | Build ticker universe (Russell 2000 + dynamic adds) |
| 2.5 | Scheduled daily data refresh |
| **Deliverable** | Populated SQLite database with 20+ years of historical data |

## Phase 3: Research Pipeline
| Task | Description |
|------|-------------|
| 3.1 | Implement Reddit scanner (PRAW streaming, ticker extraction, VADER sentiment) |
| 3.2 | Implement SEC filings analyzer (edgartools, 10-K/10-Q parsing) |
| 3.3 | Implement news sentiment (Finnhub + FinBERT) |
| 3.4 | Implement technical screen pre-filter |
| 3.5 | Implement gem detector (multi-signal confluence scoring 0-100) |
| 3.6 | Implement validation layer (cross-reference, pump-and-dump detection) |
| **Deliverable** | Pipeline that produces scored gem alerts with evidence URLs |

## Phase 4: Telegram Bot
| Task | Description |
|------|-------------|
| 4.1 | Set up python-telegram-bot |
| 4.2 | Implement gem alert formatting and delivery |
| 4.3 | Implement daily P&L report |
| 4.4 | Implement trade execution notifications |
| 4.5 | Implement tax reserve reminders |
| **Deliverable** | Full notification pipeline |

## Phase 5: Strategy Engine
| Task | Description |
|------|-------------|
| 5.1 | Implement technical indicator library (RSI, MACD, ATR, Bollinger, VWAP, ADX) |
| 5.2 | Implement Mean Reversion strategy |
| 5.3 | Implement Momentum Breakout strategy |
| 5.4 | Implement Earnings Momentum strategy |
| 5.5 | Implement ensemble layer with dynamic weighting |
| 5.6 | Implement capital-adaptive tier system |
| **Deliverable** | All 3 strategies generating signals |

## Phase 6: Backtesting
| Task | Description |
|------|-------------|
| 6.1 | Set up vectorbt engine |
| 6.2 | Implement walk-forward analysis (anchored) |
| 6.3 | Implement Optuna hyperparameter optimization |
| 6.4 | Define performance metrics (Sharpe, Sortino, Calmar, etc.) |
| 6.5 | Implement anti-overfitting checks |
| 6.6 | Run backtest on 2019-2025 data, document results |
| **Deliverable** | Validated backtest results with walk-forward equity curve |

## Phase 7: Risk Management
| Task | Description |
|------|-------------|
| 7.1 | Implement ATR-based position sizing |
| 7.2 | Implement PDT tracker (rolling 5-day window) |
| 7.3 | Implement drawdown controller (kill switch at 20%) |
| 7.4 | Implement tax reserve manager |
| 7.5 | Implement correlation check |
| 7.6 | Implement emergency procedures |
| **Deliverable** | Full risk management layer |

## Phase 8: Alpaca Integration
| Task | Description |
|------|-------------|
| 8.1 | Set up alpaca-py with paper trading credentials |
| 8.2 | Implement order placement (market + limit) |
| 8.3 | Implement position tracking and P&L calculation |
| 8.4 | Implement order status monitoring |
| 8.5 | Test paper trading with simulated orders |
| **Deliverable** | Paper trading operational |

## Phase 9: Self-Improvement System
| Task | Description |
|------|-------------|
| 9.1 | Implement trade tracer (structured JSON logging) |
| 9.2 | Implement 6-phase trace analyzer |
| 9.3 | Implement skillbook with quality gates |
| 9.4 | Implement metrics baseline system |
| 9.5 | Implement ratchet loop (keep/revert) |
| 9.6 | Implement strategy versioning |
| 9.7 | Schedule weekly improvement cron job |
| **Deliverable** | Self-improvement loop running automatically |

## Phase 10: FastAPI Backend
| Task | Description |
|------|-------------|
| 10.1 | Create FastAPI application scaffold |
| 10.2 | Implement `/api/account` endpoints |
| 10.3 | Implement `/api/alerts` endpoints |
| 10.4 | Implement `/api/portfolio` endpoints |
| 10.5 | Implement `/api/strategies` endpoints |
| 10.6 | Implement `/api/settings` endpoints |
| 10.7 | Implement `/ws/updates` WebSocket for real-time data |
| 10.8 | Implement APScheduler for trading engine jobs |
| **Deliverable** | Full REST + WebSocket API |

## Phase 11: React PWA Frontend
| Task | Description |
|------|-------------|
| 11.1 | Scaffold Vite + React + TypeScript project |
| 11.2 | Set up Tailwind CSS + shadcn/ui with dark theme |
| 11.3 | Build Dashboard page with equity chart |
| 11.4 | Build Alerts page with gem cards |
| 11.5 | Build Portfolio page with positions and history |
| 11.6 | Build Strategies page with toggles and metrics |
| 11.7 | Build Settings page with all configuration |
| 11.8 | Implement TabBar bottom navigation |
| 11.9 | Implement PWA (manifest, service worker, install prompt) |
| 11.10 | Implement WebSocket real-time updates |
| 11.11 | Implement offline support |
| **Deliverable** | Installable PWA with full functionality |

## Phase 12: NAS Deployment
| Task | Description |
|------|-------------|
| 12.1 | Finalize Dockerfile and docker-compose.yml |
| 12.2 | Copy project to Ugreen NAS |
| 12.3 | Build container on NAS |
| 12.4 | Set up Cloudflare Tunnel |
| 12.5 | Verify HTTPS access from phone |
| 12.6 | Install PWA on phone via Add to Home Screen |
| 12.7 | Verify push notifications work |
| **Deliverable** | Production deployment on NAS |

## Phase 13: Live Trading Graduation
| Task | Description |
|------|-------------|
| 13.1 | Run 4+ weeks paper trading (Phase 8-9 overlap) |
| 13.2 | Compare paper results to backtest expectations |
| 13.3 | Set up live Alpaca account with $200 |
| 13.4 | Configure tax reserve and risk parameters |
| 13.5 | Go live — first trade with real money |
| 13.6 | Monitor daily, weekly reports |
| 13.7 | First self-improvement cycle on live data |
| **Deliverable** | $200 live account, compounding toward $25,000+ |

---

## Phase Dependencies

```
Phase 1 (Foundation)
  ├──▶ Phase 2 (Data)
  │      └──▶ Phase 3 (Research) ──▶ Phase 4 (Telegram)
  │             └──▶ Phase 5 (Strats) ──▶ Phase 6 (Backtest)
  │                    └──▶ Phase 7 (Risk) ──▶ Phase 8 (Alpaca)
  │                           └──▶ Phase 9 (Self-Improve)
  │
  └──▶ Phase 10 (API) ── requires Phases 2-9 complete
         └──▶ Phase 11 (PWA) ── requires Phase 10
                └──▶ Phase 12 (Deploy) ── requires Phase 11
                       └──▶ Phase 13 (LIVE) ── requires Phase 12
```

---

## Time Estimate

| Phase | Estimated Days | Cumulative |
|-------|:-----------:|:----------:|
| 1. Foundation | 1-2 | 2 |
| 2. Data Pipeline | 1-2 | 4 |
| 3. Research | 2-3 | 7 |
| 4. Telegram | 1 | 8 |
| 5. Strategy Engine | 2-3 | 11 |
| 6. Backtesting | 2-3 | 14 |
| 7. Risk Management | 1-2 | 16 |
| 8. Alpaca Integration | 2 | 18 |
| 9. Self-Improvement | 3-4 | 22 |
| 10. FastAPI Backend | 2-3 | 25 |
| 11. React PWA | 4-6 | 31 |
| 12. NAS Deployment | 1-2 | 33 |
| 13. Live Trading | Ongoing | — |

Build time (full-time): ~5-6 weeks to live trading.
Part-time (evenings/weekends): ~10-12 weeks.
