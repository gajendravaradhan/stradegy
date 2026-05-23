from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger

from stradegy.db import async_session
from stradegy.engine.data.store import DataStore
from stradegy.engine.research.earnings_scanner import EarningsScanner
from stradegy.engine.research.openinsider_scraper import OpenInsiderScraper
from stradegy.engine.research.technical_filter import TechnicalFilter


class PreMarketScanner:
    def __init__(self):
        self.insider = OpenInsiderScraper()
        self.earnings = EarningsScanner()

    async def scan(self) -> dict[str, Any]:
        watchlist = []
        try:
            insider_signals = await self.insider.scan_recent(days=1)
            clusters = [s for s in insider_signals if s.is_cluster]
            for signal in clusters[:10]:
                watchlist.append({
                    "ticker": signal.ticker_symbol,
                    "source": "insider_cluster",
                    "score": 15,
                    "detail": f"{len([c for c in clusters if c.ticker_symbol == signal.ticker_symbol])} insiders buying",
                })
        except Exception as e:
            logger.warning(f"Pre-market insider scan error: {e}")

        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
            earnings = await self.earnings.scan_upcoming(from_date=today, to_date=tomorrow)
            for e in earnings[:10]:
                if e.days_until == 0:
                    watchlist.append({
                        "ticker": e.ticker_symbol,
                        "source": "earnings_today",
                        "score": 10,
                        "detail": f"EPS est: {e.eps_estimate}",
                    })
        except Exception as e:
            logger.warning(f"Pre-market earnings scan error: {e}")

        try:
            async with async_session() as session:
                store = DataStore(session)
                tickers = await store.get_active_tickers()
                for ticker in [t.symbol for t in tickers[:30]]:
                    try:
                        tech_filter = TechnicalFilter(store)
                        technical = await tech_filter.analyze(ticker)
                        if technical and technical.overall_pass and technical.passes_rsi_filter:
                            watchlist.append({
                                "ticker": ticker,
                                "source": "technical_setup",
                                "score": 8,
                                "detail": f"RSI: {technical.rsi_14:.1f}",
                            })
                    except Exception as e:
                        logger.debug(f"Pre-market technical skip {ticker}: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Pre-market technical scan error: {e}")

        unique = {}
        for item in watchlist:
            t = item["ticker"]
            if t not in unique or item["score"] > unique[t]["score"]:
                unique[t] = item

        sorted_watchlist = sorted(unique.values(), key=lambda x: x["score"], reverse=True)[:20]
        logger.info(f"Pre-market watchlist: {len(sorted_watchlist)} tickers")
        return {
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "watchlist": sorted_watchlist,
        }
