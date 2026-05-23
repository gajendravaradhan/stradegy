import asyncio
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger

from stradegy.engine.research.reddit_scanner import RedditScanner
from stradegy.engine.research.stocktwits_scanner import StockTwitsScanner


class SocialStreamMonitor:
    def __init__(self):
        self.reddit = RedditScanner()
        self.stocktwits = StockTwitsScanner()
        self._running = False
        self._mentions_buffer: deque[dict[str, Any]] = deque(maxlen=500)
        self._last_check = datetime.now(timezone.utc)
        self._lock = asyncio.Lock()

    async def start_streaming(self):
        if self._running:
            return
        self._running = True
        logger.info("Social stream monitor started")
        try:
            while self._running:
                try:
                    if not await self._is_market_hours():
                        await asyncio.sleep(300)
                        continue
                    reddit_mentions = await self.reddit.scan_hot(limit=25)
                    stocktwits_mentions = await self.stocktwits.scan_hot(limit=25)
                    all_mentions = []
                    for m in reddit_mentions:
                        all_mentions.append({
                            "source": "reddit",
                            "ticker": m.ticker_symbol,
                            "sentiment": m.sentiment_compound,
                            "url": m.post_url,
                            "time": m.created_utc.isoformat(),
                        })
                    for m in stocktwits_mentions:
                        all_mentions.append({
                            "source": "stocktwits",
                            "ticker": m.ticker_symbol,
                            "sentiment": m.sentiment_compound,
                            "url": m.message_url,
                            "time": m.created_utc.isoformat(),
                        })
                    async with self._lock:
                        for mention in all_mentions:
                            self._mentions_buffer.append(mention)
                        self._last_check = datetime.now(timezone.utc)
                    await asyncio.sleep(120)
                except Exception as e:
                    logger.warning(f"Social stream error: {e}")
                    await asyncio.sleep(60)
        finally:
            self._running = False
            logger.info("Social stream monitor loop exited")

    async def _is_market_hours(self) -> bool:
        now = datetime.now(timezone.utc)
        if now.weekday() >= 5:
            return False
        from zoneinfo import ZoneInfo
        et = now.astimezone(ZoneInfo("US/Eastern"))
        market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= et < market_close

    async def get_recent_mentions(self, ticker: str, minutes: int = 15) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        async with self._lock:
            return [
                m for m in self._mentions_buffer
                if m["ticker"].upper() == ticker.upper() and datetime.fromisoformat(m["time"]) > cutoff
            ]

    async def stop(self):
        self._running = False
        logger.info("Social stream monitor stopped")

    async def close(self):
        await self.stop()
        await self.reddit.close()
        await self.stocktwits.close()
