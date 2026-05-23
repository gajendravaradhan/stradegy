import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "stradegy.log"
logger.add(LOG_FILE, rotation="10 MB", retention="7 days", level="INFO")

from stradegy.config import settings
from stradegy.db import get_db, init_db, Trade as TradeModel

from stradegy.engine.research.db import (
    DiscordMentionRecord,
    GemSignalRecord,
    NewsSentimentRecord,
    RedditMentionRecord,
    SECFilingRecord,
)

_sqlalchemy_registered_research_tables = [
    RedditMentionRecord,
    DiscordMentionRecord,
    SECFilingRecord,
    NewsSentimentRecord,
    GemSignalRecord,
]

from stradegy.engine.data.fetcher import DataFetcher
from stradegy.engine.data.store import DataStore
from stradegy.engine.data.ticker_universe import TickerUniverse


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        async for session in get_db():
            store = DataStore(session)
            count = await universe.seed_tickers_to_db(store)
            logger.info(f"Auto-seeded {count} tickers on startup")
            break
    except Exception as e:
        logger.warning(f"Auto-seed tickers failed: {e}")
    scheduler.start()
    logger.info("APScheduler started")
    yield
    scheduler.shutdown()
    logger.info("APScheduler shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api/account/summary")
async def account_summary():
    from stradegy.engine.risk.tiers import get_tier_config
    return {
        "equity": 0.0,
        "buying_power": 0.0,
        "tax_reserve": 0.0,
        "day_pnl": 0.0,
        "open_positions": 0,
        "mode": "paper" if settings.paper_trading else "live",
        "autonomy": settings.autonomy_mode,
        "tier": get_tier_config(0.0),
    }


universe = TickerUniverse()


@app.post("/api/data/backfill")
async def backfill_tickers(
    symbols: list[str] | None = None,
    batch_size: int = 50,
):
    if not symbols:
        symbols = universe.get_active_universe()

    logger.info(f"Starting backfill for {len(symbols)} tickers")

    async for session in get_db():
        store = DataStore(session)
        fetcher = DataFetcher()
        results = await fetcher.fetch_tickers(symbols, period="20y")

        total_inserted = 0
        for symbol, records in results.items():
            if records:
                inserted = await store.save_ohlcv_batch(records)
                total_inserted += inserted

        return {
            "success": True,
            "tickers_processed": len(symbols),
            "total_rows_inserted": total_inserted,
        }


@app.post("/api/data/incremental")
async def incremental_update(
    symbols: list[str] | None = None,
):
    if not symbols:
        symbols = universe.get_active_universe()

    logger.info(f"Starting incremental update for {len(symbols)} tickers")

    async for session in get_db():
        store = DataStore(session)
        fetcher = DataFetcher()

        updated = 0
        skipped = 0
        failed = 0

        for symbol in symbols:
            latest = await store.get_latest_date(symbol)
            try:
                records = await fetcher.fetch_incremental(symbol, latest)
                if records:
                    await store.save_ohlcv_batch(records)
                    updated += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Failed incremental update for {symbol}: {e}")
                failed += 1

        return {
            "success": True,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
        }


@app.get("/api/data/tickers")
async def list_tickers(
    active_only: bool = Query(default=True),
    watched_only: bool = Query(default=False),
):
    from sqlalchemy import select
    from stradegy.db import Ticker as TickerModel

    async for session in get_db():
        stmt = select(TickerModel)
        if active_only:
            stmt = stmt.where(TickerModel.is_active == True)
        if watched_only:
            stmt = stmt.where(TickerModel.is_watched == True)

        result = await session.execute(stmt)
        tickers = result.scalars().all()
        return [
            {
                "symbol": t.symbol,
                "name": t.name,
                "sector": t.sector,
                "is_active": t.is_active,
                "is_watched": t.is_watched,
            }
            for t in tickers
        ]


@app.post("/api/data/tickers/seed")
async def seed_tickers():
    async for session in get_db():
        store = DataStore(session)
        count = await universe.seed_tickers_to_db(store)
        return {"success": True, "tickers_seeded": count}


@app.get("/api/data/tickers/{symbol}")
async def get_ticker_detail(symbol: str):
    async for session in get_db():
        store = DataStore(session)
        ticker = await store.get_ticker(symbol.upper())
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
        return {
            "symbol": ticker.symbol,
            "name": ticker.name,
            "sector": ticker.sector,
            "is_active": ticker.is_active,
            "is_watched": ticker.is_watched,
        }


@app.get("/api/data/tickers/{symbol}/range")
async def get_data_range(symbol: str):
    async for session in get_db():
        store = DataStore(session)
        oldest, newest = await store.get_data_range(symbol)
        return {
            "symbol": symbol.upper(),
            "oldest_date": oldest.isoformat() if oldest else None,
            "newest_date": newest.isoformat() if newest else None,
            "days_of_data": (newest - oldest).days + 1 if oldest and newest else 0,
        }


@app.post("/api/data/tickers/{symbol}/watch")
async def toggle_watch_ticker(symbol: str):
    async for session in get_db():
        store = DataStore(session)
        ticker = await store.get_ticker(symbol.upper())
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
        updated = await store.update_ticker(symbol, is_watched=not ticker.is_watched)
        return {
            "symbol": updated.symbol,
            "is_watched": updated.is_watched,
        }


@app.get("/api/data/tickers/{symbol}/sparkline")
async def get_sparkline(symbol: str, days: int = 90):
    async for session in get_db():
        store = DataStore(session)
        records = await store.get_ticker_data(symbol.upper(), limit=days)
        return [
            {"date": r.date.isoformat(), "close": float(r.close)}
            for r in records
        ]


@app.get("/api/data/tickers/{symbol}/ohlcv")
async def get_ohlcv(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=100, le=5000),
):
    async for session in get_db():
        store = DataStore(session)
        records = await store.get_ticker_data(
            symbol, start_date=start_date, end_date=end_date, limit=limit
        )
        return [
            {
                "date": r.date.isoformat(),
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": r.volume,
                "adjusted_close": float(r.adjusted_close) if r.adjusted_close else None,
            }
            for r in records
        ]


@app.get("/api/alerts")
async def get_alerts(min_score: float = Query(default=50.0, ge=0.0, le=100.0), limit: int = Query(default=20, le=100)):
    from stradegy.engine.research.db import ResearchStore
    async for session in get_db():
        store = ResearchStore(session)
        gems = await store.get_gem_signals(min_score=min_score, limit=limit)
        return [
            {
                "id": g.id,
                "ticker": g.ticker_symbol,
                "score": g.total_score,
                "classification": g.classification,
                "source_count": g.source_count,
                "reddit": g.reddit_score,
                "discord": g.discord_score,
                "sec": g.sec_score,
                "news": g.news_score,
                "technical": g.technical_score,
                "status": g.status,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in gems
        ]


@app.post("/api/alerts/{gem_id}/approve")
async def approve_alert(gem_id: int):
    from stradegy.engine.research.db import ResearchStore
    async for session in get_db():
        store = ResearchStore(session)
        gem = await store.approve_gem(gem_id)
        if not gem:
            return {"success": False, "error": "Gem not found"}

        order_result = None
        if settings.autonomy_mode == "semi":
            try:
                from stradegy.engine.execution.alpaca_client import AlpacaClient
                from stradegy.engine.risk.manager import RiskManager
                from stradegy.engine.data.store import DataStore

                client = AlpacaClient()
                account = await client.get_account()
                if not account:
                    return {"success": False, "error": "Could not fetch Alpaca account"}

                equity = account.get("equity", 0.0)
                ds = DataStore(session)
                rm = RiskManager()

                history = await ds.get_portfolio_history(days=90)
                peak_equity = equity
                for h in history:
                    if h.get("peak_equity") and h["peak_equity"] > peak_equity:
                        peak_equity = h["peak_equity"]
                    elif h.get("equity") and h["equity"] > peak_equity:
                        peak_equity = h["equity"]

                pdt_data = rm.check_pdt([])
                emergency = rm.emergency_check(equity, peak_equity, pdt_data, [])
                if emergency["should_halt_trading"]:
                    logger.warning(f"TRADING HALTED: {emergency['emergencies']}")
                    return {
                        "success": False,
                        "error": f"Trading halted: {'; '.join(emergency['emergencies'])}",
                        "gem_id": gem_id,
                    }

                from datetime import datetime
                import pytz
                et = pytz.timezone("US/Eastern")
                now = datetime.now(et)
                market_closed = (
                    now.weekday() >= 5
                    or now.hour < 9
                    or (now.hour == 9 and now.minute < 30)
                    or now.hour >= 16
                )
                if market_closed:
                    return {
                        "success": False,
                        "error": "Market is closed. Orders allowed only during market hours (Mon-Fri 9:30-16:00 ET).",
                        "gem_id": gem_id,
                    }

                positions = await client.get_positions()
                tier = rm._tier_config(equity)
                if len(positions) >= tier["max_positions"]:
                    return {
                        "success": False,
                        "error": f"Max positions reached ({len(positions)}/{tier['max_positions']}) for tier {tier['tier']}.",
                        "gem_id": gem_id,
                    }

                df = await ds.get_ohlcv_dataframe(gem.ticker_symbol, limit=30)
                atr = 0.0
                if df is not None and len(df) >= 14:
                    import pandas as pd
                    hl = df["high"] - df["low"]
                    hc = abs(df["high"] - df["close"].shift())
                    lc = abs(df["low"] - df["close"].shift())
                    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
                    atr = tr.rolling(window=14).mean().iloc[-1]

                latest_price = await ds.get_latest_price(gem.ticker_symbol)
                price = float(latest_price) if latest_price else 0.0

                sizing = rm.calculate_position_size(equity, atr, price)
                if sizing["shares"] <= 0:
                    return {
                        "success": False,
                        "error": f"Position sizing returned 0 shares (price={price}, atr={atr}).",
                        "gem_id": gem_id,
                    }

                order_result = await client.submit_order(
                    symbol=gem.ticker_symbol,
                    qty=sizing["shares"],
                    side="buy",
                    order_type="market",
                )
                if order_result and not order_result.get("error"):
                    order_id = order_result.get("id")
                    if order_id:
                        fill_result = await client.poll_order_fill(order_id, timeout=30, interval=2)
                        order_result["fill_status"] = fill_result
                        if fill_result.get("status", "").lower() == "filled":
                            await store.execute_gem(gem_id)
                            logger.info(
                                f"Order filled for {gem.ticker_symbol}: {fill_result.get('filled_qty', 0)}/{fill_result.get('qty', 0)} shares"
                            )
                            filled_qty = float(fill_result.get("filled_qty", sizing["shares"]))
                            trade = TradeModel(
                                ticker_symbol=gem.ticker_symbol,
                                action="buy",
                                price=Decimal(str(price)),
                                shares=int(filled_qty),
                                strategy="ensemble",
                                signal_confidence=gem.total_score / 100.0,
                                order_id=str(order_id),
                                status="filled",
                                mode="paper" if settings.paper_trading else "live",
                                gem_id=gem_id,
                                notes=f"Auto-executed via approve_alert. ATR={atr:.2f}",
                            )
                            session.add(trade)
                            await session.commit()
                        else:
                            logger.warning(
                                f"Order {order_id} not filled: status={fill_result.get('status')}, timeout={fill_result.get('poll_timeout')}"
                            )
                    else:
                        await store.execute_gem(gem_id)
                        logger.info(f"Order submitted for {gem.ticker_symbol} (no order ID to poll)")
            except Exception as e:
                logger.error(f"Failed to execute approved gem {gem_id}: {e}")
                order_result = {"error": str(e)}

        return {
            "success": True,
            "gem_id": gem_id,
            "status": gem.status,
            "order": order_result,
        }


@app.post("/api/alerts/{gem_id}/reject")
async def reject_alert(gem_id: int):
    from stradegy.engine.research.db import ResearchStore
    async for session in get_db():
        store = ResearchStore(session)
        gem = await store.reject_gem(gem_id)
        if not gem:
            return {"success": False, "error": "Gem not found"}
        return {"success": True, "gem_id": gem_id, "status": gem.status}


@app.get("/api/portfolio")
async def get_portfolio():
    equity = 0.0
    buying_power = 0.0
    positions = []
    day_pnl = 0.0
    tax_reserve = 0.0
    realized_gains = 0.0
    try:
        from stradegy.engine.execution.alpaca_client import AlpacaClient
        client = AlpacaClient()
        account = await client.get_account()
        if account:
            equity = account.get("equity", 0.0)
            buying_power = account.get("buying_power", 0.0)
            day_pnl = account.get("equity", 0.0) - account.get("last_equity", account.get("equity", 0.0))
        positions = await client.get_positions()
    except Exception as e:
        logger.warning(f"Could not fetch Alpaca portfolio: {e}")

    from stradegy.engine.risk.tiers import get_tier_config
    tier = get_tier_config(equity)

    async for session in get_db():
        store = DataStore(session)
        try:
            latest_snapshot = await store.get_portfolio_history(days=1)
            if latest_snapshot and len(latest_snapshot) > 0:
                snap = latest_snapshot[-1]
                if equity == 0.0:
                    equity = float(snap.get("equity", 0.0))
                    buying_power = float(snap.get("buying_power", 0.0))
                tax_reserve = float(snap.get("tax_reserve", 0.0))
                realized_gains = float(snap.get("realized_gains", 0.0))
                if day_pnl == 0.0:
                    day_pnl = float(snap.get("day_pnl", 0.0))
        except Exception as e:
            logger.warning(f"Could not fetch portfolio snapshot: {e}")
        break

    return {
        "equity": equity,
        "buying_power": buying_power,
        "tax_reserve": tax_reserve,
        "day_pnl": round(day_pnl, 2),
        "open_positions": len(positions),
        "positions": positions,
        "realized_gains": realized_gains,
        "mode": "paper" if settings.paper_trading else "live",
        "autonomy": settings.autonomy_mode,
        "tier": tier,
    }


@app.get("/api/portfolio/history")
async def get_portfolio_history(days: int = 90):
    from stradegy.engine.data.store import DataStore
    async for session in get_db():
        store = DataStore(session)
        history = await store.get_portfolio_history(days=days)
        return {
            "days": days,
            "count": len(history),
            "history": history,
        }
    return {"days": days, "count": 0, "history": []}


@app.get("/api/portfolio/metrics")
async def get_portfolio_metrics(days: int = 90):
    from stradegy.engine.performance import get_performance_metrics
    metrics = get_performance_metrics(days=days)
    return metrics


@app.get("/api/strategies")
async def get_strategies():
    return {
        "strategies": [
            {
                "name": "Mean Reversion",
                "active": True,
                "weight": 0.33,
                "description": "Buy oversold, sell overbought using RSI + Bollinger Bands",
            },
            {
                "name": "Momentum Breakout",
                "active": True,
                "weight": 0.33,
                "description": "Buy breakouts above 20-day high with volume + ADX confirmation",
            },
            {
                "name": "Earnings Momentum",
                "active": True,
                "weight": 0.34,
                "description": "Buy MACD crossovers with volume confirmation",
            },
        ],
        "ensemble_active": True,
        "min_confidence": 0.5,
        "min_agreement": 2,
    }


@app.get("/api/settings")
async def get_settings():
    return {
        "paper_trading": settings.paper_trading,
        "autonomy_mode": settings.autonomy_mode,
        "max_drawdown": settings.max_drawdown,
        "risk_per_trade": settings.risk_per_trade,
        "max_positions": settings.max_positions,
        "stop_atr_mult": settings.stop_atr_mult,
        "tax_rate_short_term": settings.tax_rate_short_term,
        "tax_rate_long_term": settings.tax_rate_long_term,
    }


@app.get("/api/secrets")
async def get_secrets():
    def mask(value: str) -> str:
        if not value or len(value) < 8:
            return ""
        return value[:4] + "•" * (len(value) - 8) + value[-4:]

    return {
        "alpaca_api_key": mask(settings.alpaca_api_key),
        "alpaca_secret_key": mask(settings.alpaca_secret_key),
        "finnhub_api_key": mask(settings.finnhub_api_key),
        "discord_bot_token": mask(settings.discord_bot_token),
        "discord_user_id": settings.discord_user_id,
        "discord_general_channel_id": settings.discord_general_channel_id,
    }


@app.post("/api/secrets")
async def update_secrets(payload: dict):
    from pathlib import Path
    env_path = Path(__file__).parent.parent.parent.parent / "secrets" / ".env"
    if not env_path.exists():
        env_path = Path(".env")

    lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()

    env_dict = {}
    for line in lines:
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            env_dict[key.strip()] = val.strip()

    updated = []
    for key, value in payload.items():
        if value and isinstance(value, str) and len(value) > 0:
            env_dict[key] = value
            setattr(settings, key, value)
            updated.append(key)

    with open(env_path, "w") as f:
        for key, val in env_dict.items():
            f.write(f"{key}={val}\n")

    if env_path.exists():
        import os
        os.chmod(env_path, 0o600)

    return {"success": True, "updated": updated}


@app.post("/api/settings")
async def update_settings(payload: dict):
    changed = []
    for key, value in payload.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
            changed.append(key)

    env_path = Path(__file__).parent.parent.parent.parent / "secrets" / ".env"
    if not env_path.exists():
        env_path = Path(".env")

    lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()

    env_dict = {}
    for line in lines:
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env_dict[k.strip()] = v.strip()

    for key in changed:
        val = getattr(settings, key)
        if val is not None:
            env_dict[key] = str(val).lower() if isinstance(val, bool) else str(val)

    with open(env_path, "w") as f:
        for k, v in env_dict.items():
            f.write(f"{k}={v}\n")

    if env_path.exists():
        import os
        os.chmod(env_path, 0o600)

    return {"success": True, "changed": changed}


@app.get("/api/tier")
async def get_tier(equity: float | None = None):
    from stradegy.engine.risk.tiers import get_tier_config, TIERS
    if equity is None:
        try:
            from stradegy.engine.execution.alpaca_client import AlpacaClient
            client = AlpacaClient()
            account = await client.get_account()
            equity = account.get("equity", 0.0) if account else 0.0
        except Exception:
            equity = 0.0
    return {
        "current": get_tier_config(equity),
        "all_tiers": [
            {
                "name": t.name,
                "min_equity": t.min_equity,
                "max_equity": t.max_equity,
                "max_positions": t.max_positions,
                "risk_per_trade": t.risk_per_trade,
                "description": t.description,
            }
            for t in TIERS
        ],
    }


@app.get("/api/trades")
async def list_trades(
    ticker: str | None = None,
    limit: int = Query(default=50, le=500),
    days: int = Query(default=90, le=365),
):
    from sqlalchemy import select
    async for session in get_db():
        stmt = select(TradeModel).where(TradeModel.created_at >= (datetime.now(timezone.utc) - timedelta(days=days)))
        if ticker:
            stmt = stmt.where(TradeModel.ticker_symbol == ticker.upper())
        stmt = stmt.order_by(TradeModel.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        trades = result.scalars().all()
        return {
            "count": len(trades),
            "trades": [
                {
                    "id": t.id,
                    "ticker": t.ticker_symbol,
                    "action": t.action,
                    "price": float(t.price),
                    "shares": t.shares,
                    "strategy": t.strategy,
                    "status": t.status,
                    "pnl": float(t.pnl) if t.pnl is not None else None,
                    "mode": t.mode,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "notes": t.notes,
                }
                for t in trades
            ],
        }


@app.get("/api/activity")
async def get_activity(limit: int = Query(default=20, le=100)):
    from sqlalchemy import select
    async for session in get_db():
        stmt_trades = select(TradeModel).order_by(TradeModel.created_at.desc()).limit(limit)
        result_trades = await session.execute(stmt_trades)
        trades = result_trades.scalars().all()

        stmt_gems = select(GemSignalRecord).order_by(GemSignalRecord.created_at.desc()).limit(limit)
        result_gems = await session.execute(stmt_gems)
        gems = result_gems.scalars().all()

        activity = []
        for t in trades:
            activity.append({
                "type": "trade",
                "timestamp": t.created_at.isoformat() if t.created_at else None,
                "ticker": t.ticker_symbol,
                "action": t.action,
                "details": f"{t.action.upper()} {t.shares} shares @ ${float(t.price):.2f}",
                "status": t.status,
                "pnl": float(t.pnl) if t.pnl is not None else None,
            })
        for g in gems:
            if g.status != "pending":
                activity.append({
                    "type": "gem_action",
                    "timestamp": g.actioned_at.isoformat() if g.actioned_at else (g.created_at.isoformat() if g.created_at else None),
                    "ticker": g.ticker_symbol,
                    "action": g.status,
                    "details": f"Gem {g.status}: score {g.total_score:.0f}",
                    "status": g.status,
                })
        activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return {"activity": activity[:limit]}


@app.get("/api/data/tickers/{symbol}/research")
async def get_ticker_research(symbol: str, days: int = 7):
    from stradegy.engine.research.db import ResearchStore
    from datetime import datetime, timedelta, timezone
    async for session in get_db():
        store = ResearchStore(session)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        news = await store.get_news_sentiments(symbol, limit=5)
        reddit = await store.get_reddit_mentions(symbol, limit=5)
        discord = await store.get_discord_mentions(symbol, limit=5)
        sec = await store.get_sec_filings(symbol, limit=3)
        latest_gem = await store.get_latest_gem_signal(symbol)
        return {
            "symbol": symbol.upper(),
            "news": [
                {
                    "headline": n.headline,
                    "url": n.article_url,
                    "source": n.source,
                    "sentiment": n.finbert_label,
                    "confidence": round(n.finbert_confidence, 2),
                    "published_at": n.published_at.isoformat() if n.published_at else None,
                }
                for n in news
            ],
            "reddit": [
                {
                    "title": r.title,
                    "url": r.post_url,
                    "subreddit": r.subreddit,
                    "score": r.score,
                    "sentiment": round(r.sentiment_compound, 2),
                }
                for r in reddit
            ],
            "discord": [
                {
                    "content": d.content[:200],
                    "url": d.message_url,
                    "channel": d.channel_name,
                    "reactions": d.num_reactions,
                    "sentiment": round(d.sentiment_compound, 2),
                }
                for d in discord
            ],
            "sec": [
                {
                    "filing_type": s.filing_type,
                    "filing_date": s.filing_date.isoformat() if s.filing_date else None,
                    "url": s.filing_url,
                    "revenue_growth": s.revenue_growth_yoy,
                    "insider_net_buys": s.insider_net_buys,
                }
                for s in sec
            ],
            "latest_gem": {
                "score": latest_gem.total_score if latest_gem else None,
                "classification": latest_gem.classification if latest_gem else None,
                "source_count": latest_gem.source_count if latest_gem else None,
                "status": latest_gem.status if latest_gem else None,
                "created_at": latest_gem.created_at.isoformat() if latest_gem and latest_gem.created_at else None,
            } if latest_gem else None,
        }


@app.get("/api/health/detailed")
async def detailed_health():
    from sqlalchemy import select, func
    from stradegy.db import Ticker, OHLCV, Trade as TradeModel
    from stradegy.engine.research.db import GemSignalRecord
    from stradegy.engine.data.ticker_universe import TickerUniverse
    health = {
        "version": settings.app_version,
        "mode": "paper" if settings.paper_trading else "live",
        "autonomy": settings.autonomy_mode,
        "alpaca_connected": False,
        "finnhub_connected": bool(settings.finnhub_api_key),
        "discord_connected": bool(settings.discord_bot_token),
    }
    try:
        from stradegy.engine.execution.alpaca_client import AlpacaClient
        client = AlpacaClient()
        account = await client.get_account()
        health["alpaca_connected"] = bool(account)
    except Exception:
        pass
    try:
        from stradegy.engine.research.news_scanner import NewsScanner
        ns = NewsScanner()
        health["finnhub_connected"] = ns._ensure_client()
    except Exception:
        pass
    async for session in get_db():
        store = DataStore(session)
        ticker_count = await session.scalar(select(func.count()).select_from(Ticker))
        ohlcv_count = await session.scalar(select(func.count()).select_from(OHLCV))
        gem_count = await session.scalar(select(func.count()).select_from(GemSignalRecord))
        trade_count = await session.scalar(select(func.count()).select_from(TradeModel))
        active_tickers = await store.get_active_tickers()
        latest_gem = await session.execute(select(GemSignalRecord).order_by(GemSignalRecord.created_at.desc()).limit(1))
        latest_gem = latest_gem.scalar_one_or_none()
        health["data"] = {
            "tickers": ticker_count,
            "ohlcv_rows": ohlcv_count,
            "gems": gem_count,
            "trades": trade_count,
            "active_tickers": len(active_tickers),
            "latest_gem_at": latest_gem.created_at.isoformat() if latest_gem and latest_gem.created_at else None,
        }
        break
    return health


@app.post("/api/research/scan")
async def trigger_research_scan(scan_type: str = Query(default="incremental", alias="type")):
    from stradegy.engine.research.orchestrator import ResearchOrchestrator
    orchestrator = ResearchOrchestrator()
    try:
        if scan_type == "full":
            result = await orchestrator.run_market_open_scan()
        elif scan_type == "close":
            result = await orchestrator.run_close_scan()
        elif scan_type == "weekend":
            result = await orchestrator.run_weekend_deep()
        else:
            result = await orchestrator.run_incremental_scan()
        await ws_manager.broadcast({"type": "alerts_update"})
        return {"success": True, "message": f"{scan_type} scan triggered", "result": str(result)}
    except Exception as e:
        logger.error(f"Manual scan failed: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/backtest/run")
async def run_backtest(
    ticker: str,
    strategy: str = "ensemble",
    train_size: int = 252,
    test_size: int = 63,
    step_size: int = 63,
):
    from stradegy.engine.backtest.walk_forward import WalkForwardBacktester
    from stradegy.engine.strategy.earnings_momentum import EarningsMomentumStrategy
    from stradegy.engine.strategy.ensemble import EnsembleStrategy
    from stradegy.engine.strategy.mean_reversion import MeanReversionStrategy
    from stradegy.engine.strategy.momentum_breakout import MomentumBreakoutStrategy

    strategy_map = {
        "mean_reversion": MeanReversionStrategy,
        "momentum_breakout": MomentumBreakoutStrategy,
        "earnings_momentum": EarningsMomentumStrategy,
        "ensemble": EnsembleStrategy,
    }
    strategy_cls = strategy_map.get(strategy.lower(), EnsembleStrategy)
    instance = strategy_cls()

    async for session in get_db():
        store = DataStore(session)
        df = await store.get_ohlcv_dataframe(ticker.upper(), limit=2000)
        if df is None or len(df) < train_size + test_size:
            return {"error": f"Insufficient data for {ticker}. Found {len(df) if df is not None else 0} rows."}

        backtester = WalkForwardBacktester(
            train_size=train_size,
            test_size=test_size,
            step_size=step_size,
            min_train_size=train_size,
        )
        results = backtester.run(df, ticker.upper(), instance)
        aggregated = backtester.aggregate_results(results)

        return {
            "ticker": ticker.upper(),
            "strategy": strategy,
            "windows_tested": len(results),
            "aggregate": aggregated,
            "window_results": [
                {
                    "train_start": r.train_start.isoformat(),
                    "train_end": r.train_end.isoformat(),
                    "test_start": r.test_start.isoformat(),
                    "test_end": r.test_end.isoformat(),
                    "total_return": r.total_return,
                    "sharpe_ratio": r.sharpe_ratio,
                    "max_drawdown": r.max_drawdown,
                    "win_rate": r.win_rate,
                    "total_trades": r.total_trades,
                }
                for r in results
            ],
        }


@app.get("/api/backtest/strategies")
async def list_backtest_strategies():
    return {
        "strategies": [
            {"key": "mean_reversion", "name": "Mean Reversion", "description": "RSI + Bollinger Bands"},
            {"key": "momentum_breakout", "name": "Momentum Breakout", "description": "Breakouts with ADX"},
            {"key": "earnings_momentum", "name": "Earnings Momentum", "description": "MACD + volume"},
            {"key": "ensemble", "name": "Ensemble", "description": "Consensus voting across all three"},
        ]
    }


async def daily_data_refresh():
    logger.info("Running scheduled daily data refresh")
    symbols = universe.get_active_universe()

    async for session in get_db():
        store = DataStore(session)
        fetcher = DataFetcher()

        updated = 0
        for symbol in symbols:
            latest = await store.get_latest_date(symbol)
            try:
                records = await fetcher.fetch_incremental(symbol, latest)
                if records:
                    await store.save_ohlcv_batch(records)
                    updated += 1
            except Exception as e:
                logger.error(f"Daily refresh failed for {symbol}: {e}")

        logger.info(f"Daily refresh complete: {updated} tickers updated")

        try:
            from stradegy.engine.execution.alpaca_client import AlpacaClient
            client = AlpacaClient()
            account = await client.get_account()
            if account:
                from datetime import date
                from decimal import Decimal
                equity = Decimal(str(account.get("equity", 0)))
                bp = Decimal(str(account.get("buying_power", 0)))
                positions = await client.get_positions()

                history = await store.get_portfolio_history(days=90)
                peak_equity = equity
                for h in history:
                    if h.get("peak_equity") and h["peak_equity"] > peak_equity:
                        peak_equity = Decimal(str(h["peak_equity"]))
                    elif h.get("equity") and h["equity"] > peak_equity:
                        peak_equity = Decimal(str(h["equity"]))

                drawdown = 0.0
                if peak_equity > 0:
                    drawdown = float((peak_equity - equity) / peak_equity)

                await store.save_portfolio_snapshot({
                    "date": date.today(),
                    "equity": equity,
                    "buying_power": bp,
                    "open_positions": len(positions),
                    "peak_equity": peak_equity,
                    "drawdown": drawdown,
                })
                logger.info(f"Portfolio snapshot recorded: equity={equity}, peak={peak_equity}, dd={drawdown:.2%}")
                await ws_manager.broadcast({"type": "portfolio_update"})
        except Exception as e:
            logger.warning(f"Portfolio snapshot failed: {e}")


async def run_self_improvement_cycle():
    logger.info("Running scheduled self-improvement cycle")
    try:
        from stradegy.engine.self_improvement.orchestrator import SelfImprovementOrchestrator
        orchestrator = SelfImprovementOrchestrator()
        async for session in get_db():
            store = DataStore(session)
            result = await orchestrator.run_daily_cycle(store)
            logger.info(f"Self-improvement cycle result: {result}")
            await ws_manager.broadcast({"type": "metrics_update"})
            break
    except Exception as e:
        logger.error(f"Self-improvement cycle failed: {e}")


async def send_daily_discord_report():
    logger.info("Running scheduled daily Discord report")
    try:
        from stradegy.engine.research.discord_reporter import DiscordReporter
        reporter = DiscordReporter()

        equity = 0.0
        day_pnl = 0.0
        positions = []
        try:
            from stradegy.engine.execution.alpaca_client import AlpacaClient
            client = AlpacaClient()
            account = await client.get_account()
            if account:
                equity = account.get("equity", 0.0)
            positions = await client.get_positions()
        except Exception as e:
            logger.warning(f"Could not fetch Alpaca data for daily report: {e}")

        data = {
            "equity": equity,
            "day_pnl": day_pnl,
            "day_pnl_pct": 0.0,
            "open_positions": len(positions),
            "positions": positions,
            "gems_found": 0,
            "mode": "paper" if settings.paper_trading else "live",
        }

        await reporter.send_daily_report(data)
        await reporter.close()
    except Exception as e:
        logger.error(f"Daily Discord report failed: {e}")


async def send_monthly_discord_report():
    logger.info("Running scheduled monthly Discord report")
    try:
        from stradegy.engine.research.discord_reporter import DiscordReporter
        from stradegy.engine.strategy.reviewer import StrategyReviewer

        reviewer = StrategyReviewer()
        report = reviewer.review_monthly()

        reporter = DiscordReporter()

        if report["has_data"]:
            total_pnl = sum(s["total_pnl"] for s in report["strategies"])
            total_trades = sum(s["total_trades"] for s in report["strategies"])
            avg_win_rate = (
                sum(s["win_rate"] for s in report["strategies"]) / len(report["strategies"])
                if report["strategies"] else 0
            )
            avg_sharpe = (
                sum(s["sharpe"] for s in report["strategies"]) / len(report["strategies"])
                if report["strategies"] else 0
            )
            max_dd = max((s["max_drawdown"] for s in report["strategies"]), default=0)

            best = max(report["strategies"], key=lambda s: s["total_pnl"], default=None)
            worst = min(report["strategies"], key=lambda s: s["total_pnl"], default=None)

            data = {
                "total_return": total_pnl,
                "sharpe": avg_sharpe,
                "max_drawdown": max_dd,
                "win_rate": avg_win_rate,
                "total_trades": total_trades,
                "best_performer": f"{best['name']} (${best['total_pnl']:,.2f})" if best else "N/A",
                "worst_performer": f"{worst['name']} (${worst['total_pnl']:,.2f})" if worst else "N/A",
                "adjustments": [r["suggested_action"] for r in report["recommendations"]],
            }
        else:
            data = {
                "total_return": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "best_performer": "N/A",
                "worst_performer": "N/A",
                "adjustments": ["No trades in the last 30 days"],
            }

        await reporter.send_monthly_report(data)
        await reporter.close()
    except Exception as e:
        logger.error(f"Monthly Discord report failed: {e}")


async def send_quarterly_discord_report():
    logger.info("Running scheduled quarterly Discord report")
    try:
        from stradegy.engine.research.discord_reporter import DiscordReporter
        from stradegy.engine.strategy.reviewer import StrategyReviewer

        reviewer = StrategyReviewer()
        report = reviewer.review_quarterly()

        reporter = DiscordReporter()

        if report["has_data"]:
            total_pnl = sum(s["total_pnl"] for s in report["strategies"])
            total_trades = sum(s["total_trades"] for s in report["strategies"])
            avg_win_rate = (
                sum(s["win_rate"] for s in report["strategies"]) / len(report["strategies"])
                if report["strategies"] else 0
            )
            avg_sharpe = (
                sum(s["sharpe"] for s in report["strategies"]) / len(report["strategies"])
                if report["strategies"] else 0
            )
            max_dd = max((s["max_drawdown"] for s in report["strategies"]), default=0)

            data = {
                "total_return": total_pnl,
                "annualized_return": total_pnl * 4,
                "sharpe": avg_sharpe,
                "max_drawdown": max_dd,
                "win_rate": avg_win_rate,
                "strategy_changes": [r["suggested_action"] for r in report["recommendations"]],
                "midterm_goals": [g["goal"] for g in report.get("midterm_goals", [])],
            }
        else:
            data = {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "strategy_changes": ["No trades in the last 90 days"],
                "midterm_goals": [],
            }

        await reporter.send_quarterly_report(data)
        await reporter.close()
    except Exception as e:
        logger.error(f"Quarterly Discord report failed: {e}")


async def _research_scan_with_broadcast(scan_fn, label: str):
    try:
        result = await scan_fn()
        logger.info(f"{label} complete: {result}")
        await ws_manager.broadcast({"type": "alerts_update"})
        return result
    except Exception as e:
        logger.error(f"{label} failed: {e}")
        raise


def schedule_jobs():
    scheduler.add_job(
        daily_data_refresh,
        "cron",
        hour=20,
        minute=0,
        id="daily_data_refresh",
        replace_existing=True,
    )
    logger.info("Scheduled daily data refresh for 20:00 UTC")

    scheduler.add_job(
        run_self_improvement_cycle,
        "cron",
        hour=2,
        minute=0,
        id="self_improvement_daily",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduled daily self-improvement cycle for 02:00 UTC")

    scheduler.add_job(
        send_daily_discord_report,
        "cron",
        day_of_week="mon-fri",
        hour=20,
        minute=5,
        id="discord_daily_report",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("Scheduled daily Discord report for 20:05 UTC")

    scheduler.add_job(
        send_monthly_discord_report,
        "cron",
        day=1,
        hour=9,
        minute=0,
        id="discord_monthly_report",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduled monthly Discord report for 1st of month 09:00 UTC")

    scheduler.add_job(
        send_quarterly_discord_report,
        "cron",
        month="1,4,7,10",
        day=1,
        hour=9,
        minute=0,
        id="discord_quarterly_report",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduled quarterly Discord report for 1st of quarter 09:00 UTC")

    try:
        from stradegy.engine.research.orchestrator import ResearchOrchestrator
        from functools import partial
        orchestrator = ResearchOrchestrator()

        scheduler.add_job(
            partial(_research_scan_with_broadcast, orchestrator.run_market_open_scan, "Market open scan"),
            "cron",
            day_of_week="mon-fri",
            hour=13,
            minute=30,
            id="research_market_open",
            replace_existing=True,
            misfire_grace_time=300,
        )
        scheduler.add_job(
            partial(_research_scan_with_broadcast, orchestrator.run_incremental_scan, "Incremental scan"),
            "cron",
            day_of_week="mon-fri",
            hour="13-20",
            minute="*/15",
            id="research_incremental",
            replace_existing=True,
            misfire_grace_time=600,
            max_instances=1,
        )
        scheduler.add_job(
            partial(_research_scan_with_broadcast, orchestrator.run_close_scan, "Close scan"),
            "cron",
            day_of_week="mon-fri",
            hour=20,
            minute=0,
            id="research_close",
            replace_existing=True,
        )
        scheduler.add_job(
            partial(_research_scan_with_broadcast, orchestrator.run_weekend_deep, "Weekend deep scan"),
            "cron",
            day_of_week="sat",
            hour=16,
            minute=0,
            id="research_weekend_deep",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduled research pipeline jobs")
    except Exception as e:
        logger.warning(f"Failed to schedule research jobs: {e}")

    try:
        from stradegy.engine.monitoring.price_monitor import PriceMonitor
        from stradegy.engine.monitoring.risk_monitor import RiskMonitor
        from stradegy.engine.monitoring.data_quality import DataQualityAuditor
        from stradegy.engine.monitoring.correlation_monitor import CorrelationMonitor
        from stradegy.engine.research.premarket_scan import PreMarketScanner
        from stradegy.engine.research.paper_trade_logger import PaperTradeLogger
        from stradegy.engine.backtest.overnight_backtest import OvernightBacktestRunner
        from stradegy.engine.alerts.whatsapp_alerts import WhatsAppAlertManager

        async def _run_price_monitor():
            from stradegy.engine.data.store import DataStore
            monitor = PriceMonitor()
            try:
                async with async_session() as session:
                    store = DataStore(session)
                    tickers = await store.get_active_tickers()
                    await monitor.check_price_movements([t.symbol for t in tickers[:50]])
            finally:
                await monitor.close()

        async def _run_risk_monitor():
            monitor = RiskMonitor()
            whatsapp = WhatsAppAlertManager()
            try:
                result = await monitor.check_portfolio_risk()
                for alert in result.get("alerts", []):
                    if alert["severity"] == "critical" and monitor.should_alert(alert["type"], cooldown_minutes=60):
                        msg = f"CRITICAL RISK: {alert['message']}"
                        logger.warning(msg)
                        if whatsapp.enabled:
                            whatsapp.send_risk_alert(alert["type"], alert["message"])
            finally:
                pass

        async def _run_premarket_scan():
            scanner = PreMarketScanner()
            try:
                result = await scanner.scan()
                if result.get("watchlist"):
                    logger.info(f"Pre-market watchlist: {len(result['watchlist'])} tickers")
            finally:
                await scanner.insider.close()
                await scanner.earnings.close()

        async def _run_paper_trades():
            from stradegy.engine.data.store import DataStore
            logger_instance = PaperTradeLogger()
            async with async_session() as session:
                store = DataStore(session)
                tickers = await store.get_active_tickers()
                await logger_instance.log_signals([t.symbol for t in tickers[:30]])

        async def _run_data_quality():
            auditor = DataQualityAuditor()
            await auditor.run_audit()

        async def _run_correlation():
            monitor = CorrelationMonitor()
            await monitor.check_drift()

        async def _run_overnight_backtest():
            runner = OvernightBacktestRunner()
            await runner.run_nightly()

        scheduler.add_job(
            _run_price_monitor,
            "cron",
            day_of_week="mon-fri",
            hour="13-20",
            minute="*/15",
            id="price_monitor",
            replace_existing=True,
            misfire_grace_time=300,
            max_instances=1,
        )
        logger.info("Scheduled price monitor every 15min during market hours")

        scheduler.add_job(
            _run_premarket_scan,
            "cron",
            day_of_week="mon-fri",
            hour=13,
            minute=0,
            id="premarket_scan",
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info("Scheduled pre-market scan for 13:00 UTC Mon-Fri")

        scheduler.add_job(
            _run_risk_monitor,
            "cron",
            day_of_week="mon-fri",
            hour="13-20",
            minute="*/5",
            id="risk_monitor",
            replace_existing=True,
            misfire_grace_time=120,
            max_instances=1,
        )
        logger.info("Scheduled risk monitor every 5min during market hours")

        scheduler.add_job(
            _run_paper_trades,
            "cron",
            day_of_week="mon-fri",
            hour="13-20",
            minute="*/15",
            id="paper_trade_logger",
            replace_existing=True,
            misfire_grace_time=300,
            max_instances=1,
        )
        logger.info("Scheduled paper trade logger every 15min during market hours")

        scheduler.add_job(
            _run_data_quality,
            "cron",
            hour=3,
            minute=0,
            id="data_quality_audit",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduled data quality audit for 03:00 UTC daily")

        scheduler.add_job(
            _run_correlation,
            "cron",
            day_of_week="sun",
            hour=1,
            minute=0,
            id="correlation_drift",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduled correlation drift check for Sunday 01:00 UTC")

        scheduler.add_job(
            _run_overnight_backtest,
            "cron",
            day_of_week="mon-thu,sun",
            hour=22,
            minute=0,
            id="overnight_backtest",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("Scheduled overnight backtest for 22:00 UTC Mon-Thu + Sun")
    except Exception as e:
        logger.warning(f"Failed to schedule monitoring jobs: {e}")


schedule_jobs()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


ws_manager = ConnectionManager()


@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    app.mount("/icons", StaticFiles(directory=str(static_dir / "icons")), name="icons")

    @app.get("/manifest.webmanifest")
    async def serve_manifest():
        return FileResponse(
            str(static_dir / "manifest.webmanifest"),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/sw.js")
    async def serve_sw():
        return FileResponse(
            str(static_dir / "sw.js"),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(
            str(static_dir / "index.html"),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )


def main():
    import uvicorn
    uvicorn.run(
        "stradegy.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
