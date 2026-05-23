import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import StockTwitsMention
from stradegy.engine.research.sentiment import VaderSingleton


class StockTwitsScanner:
    TICKER_PATTERN = re.compile(r"\$?([A-Z]{1,5})\b")
    BLACKLIST = {
        "SPY", "QQQ", "DIA", "IWM", "VIX", "BTC", "ETH", "USDT", "BNB", "XRP",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    }
    API_BASE = "https://api.stocktwits.com/api/2"

    def __init__(self):
        self.sentiment = VaderSingleton()
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("StockTwits scanner initialized")

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        return {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}

    async def _fetch_trending(self, limit: int = 50) -> list[StockTwitsMention]:
        url = f"{self.API_BASE}/trending/symbols.json"
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                logger.warning(f"StockTwits trending API error {resp.status_code}")
                return []
            data = resp.json()
            symbols = data.get("symbols", [])[:limit]
            mentions = []
            for sym in symbols:
                ticker = sym.get("symbol", "")
                if not ticker or ticker in self.BLACKLIST:
                    continue
                mention = StockTwitsMention(
                    ticker_symbol=ticker,
                    message_id=f"trending_{ticker}",
                    message_url=f"https://stocktwits.com/symbol/{ticker}",
                    content=sym.get("title", ""),
                    created_utc=datetime.now(timezone.utc),
                    sentiment_compound=0.0,
                    likes=sym.get("watchlist_count", 0),
                    reshares=0,
                    watchlist_count=sym.get("watchlist_count", 0),
                )
                mentions.append(mention)
            logger.info(f"StockTwits trending: {len(mentions)} symbols")
            return mentions
        except Exception as e:
            logger.warning(f"StockTwits trending fetch error: {e}")
            return []

    async def _fetch_symbol_stream(self, ticker: str, limit: int = 30) -> list[StockTwitsMention]:
        url = f"{self.API_BASE}/streams/symbol/{ticker}.json"
        params = {"limit": min(limit, 30)}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            messages = data.get("messages", [])
            mentions = []
            for msg in messages:
                body = msg.get("body", "")
                tickers = self.extract_tickers(body)
                if not tickers:
                    continue
                sentiment = self.sentiment.analyze(body)
                created = msg.get("created_at")
                if created:
                    created_dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                else:
                    created_dt = datetime.now(timezone.utc)
                user = msg.get("user", {})
                author = user.get("username") if user else None
                likes = msg.get("likes", {}).get("total", 0)
                reshares = msg.get("reshares", {}).get("reshared_count", 0)
                for t in tickers:
                    mention = StockTwitsMention(
                        ticker_symbol=t,
                        message_id=str(msg.get("id", "")),
                        message_url=f"https://stocktwits.com/messages/{msg.get('id', '')}",
                        content=body[:500],
                        created_utc=created_dt,
                        sentiment_compound=sentiment["compound"],
                        likes=likes,
                        reshares=reshares,
                        watchlist_count=0,
                        author=author,
                    )
                    mentions.append(mention)
            return mentions
        except Exception as e:
            logger.warning(f"StockTwits stream error for {ticker}: {e}")
            return []

    async def scan_hot(self, limit: int = 50) -> list[StockTwitsMention]:
        trending = await self._fetch_trending(limit)
        all_mentions = list(trending)
        for mention in trending[:10]:
            try:
                stream = await self._fetch_symbol_stream(mention.ticker_symbol, limit=10)
                all_mentions.extend(stream)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"StockTwits stream error for {mention.ticker_symbol}: {e}")
        logger.info(f"StockTwits scan complete: {len(all_mentions)} mentions")
        return all_mentions

    async def scan_ticker(self, ticker: str, limit: int = 30) -> list[StockTwitsMention]:
        return await self._fetch_symbol_stream(ticker, limit)

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
