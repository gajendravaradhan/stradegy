# Dependencies — Complete Library List

## Backend (Python)

### Core
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.0 | REST + WebSocket API framework |
| uvicorn | >=0.30.0 | ASGI server |
| pydantic | >=2.0 | Data validation, settings |
| pydantic-settings | >=2.0 | Environment variable loading |
| sqlalchemy | >=2.0 | ORM for SQLite |
| aiosqlite | >=0.20.0 | Async SQLite driver |
| alembic | >=1.13.0 | Database migrations |

### Trading & Market Data
| Package | Version | Purpose |
|---------|---------|---------|
| alpaca-py | >=0.43.0 | Alpaca trading API (paper + live) |
| yfinance | >=0.2.49 | Yahoo Finance EOD data |
| finnhub-python | >=2.4.28 | News, sentiment, insider transactions |
| edgartools | >=4.6.0 | SEC EDGAR filing parser |
| vectorbt | >=0.28.0 | Backtesting engine |
| pandas-ta | >=0.3.14b | Technical indicators |
| ta-lib | >=0.6.0 | Technical analysis library (optional) |

### AI / NLP
| Package | Version | Purpose |
|---------|---------|---------|
| transformers | >=4.45.0 | FinBERT via HuggingFace |
| torch | >=2.4.0 | PyTorch backend for transformers |
| vader-sentiment | >=3.3.2 | Social media sentiment scoring |

### Research & Social
| Package | Version | Purpose |
|---------|---------|---------|
| praw | >=7.8.0 | Reddit API wrapper |

### Optimization & Scheduling
| Package | Version | Purpose |
|---------|---------|---------|
| optuna | >=4.0.0 | Hyperparameter optimization |
| apscheduler | >=3.10.0 | Task scheduling (cron jobs) |
| pandas | >=2.2.0 | Data manipulation |
| numpy | >=2.0.0 | Numerical computing |

### Notification
| Package | Version | Purpose |
|---------|---------|---------|
| python-telegram-bot | >=21.0 | Telegram bot API |

### Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| python-dotenv | >=1.0.0 | .env file loading |
| pyyaml | >=6.0 | YAML config parsing |
| loguru | >=0.7.0 | Structured logging |
| httpx | >=0.28.0 | Async HTTP client |
| python-jose | >=3.3.0 | JWT (if auth needed) |
| aiohttp | >=3.10.0 | Async HTTP (WebSocket client) |

### Dev
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0.0 | Testing framework |
| pytest-asyncio | >=0.24.0 | Async test support |
| pytest-cov | >=6.0.0 | Code coverage |
| ruff | >=0.9.0 | Linting + formatting |
| mypy | >=1.13.0 | Static type checking |
| pre-commit | >=4.0.0 | Git hooks |

---

## Frontend (React / TypeScript)

### Core
| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.3.0 | UI library |
| react-dom | ^18.3.0 | React DOM renderer |
| react-router-dom | ^7.0.0 | Client-side routing |
| typescript | ^5.7.0 | Type safety |

### State & Data
| Package | Version | Purpose |
|---------|---------|---------|
| @tanstack/react-query | ^5.0.0 | Server state management, caching |
| zustand | ^5.0.0 | Client state management |

### UI & Styling
| Package | Version | Purpose |
|---------|---------|---------|
| tailwindcss | ^3.4.0 | Utility-first CSS |
| @tailwindcss/vite | ^3.4.0 | Tailwind Vite plugin |
| lucide-react | ^0.470.0 | Icon library |
| clsx | ^2.1.0 | Conditional class names |
| tailwind-merge | ^3.0.0 | Tailwind class merging |
| class-variance-authority | ^0.7.0 | Component variants |

### Charts
| Package | Version | Purpose |
|---------|---------|---------|
| @tremor/react | ^3.18.0 | Recharts-based financial charts |
| recharts | ^2.15.0 | Chart library (Tremor dependency) |

### shadcn/ui Components Used
- Card, Badge, Button, Input, Label, Switch, Tabs, Sheet, Dialog
- Select, Toggle, Tooltip, Separator, Skeleton
- ScrollArea, Drawer (for bottom sheets)

### PWA
| Package | Version | Purpose |
|---------|---------|---------|
| vite-plugin-pwa | ^0.21.0 | PWA manifest, service worker |
| workbox-window | ^7.0.0 | Service worker registration |

### Dev
| Package | Version | Purpose |
|---------|---------|---------|
| vite | ^6.0.0 | Build tool |
| @vitejs/plugin-react | ^4.0.0 | Vite React plugin |
| @types/react | ^18.3.0 | React type definitions |
| @types/react-dom | ^18.3.0 | React DOM type definitions |
| eslint | ^9.0.0 | Linting |
| prettier | ^3.5.0 | Formatting |

---

## Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2+ | Container orchestration |
| Python | 3.12+ | Runtime |
| Node.js | 22+ | Frontend build |
| npm | 10+ | Package manager |
| Cloudflare Tunnel | latest | Secure remote access |
| Git | 2.45+ | Version control |
