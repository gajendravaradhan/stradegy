import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import TelegramMention
from stradegy.engine.research.sentiment import VaderSingleton


class TelegramScanner:
    TICKER_PATTERN = re.compile(r"\$?([A-Z]{1,5})\b")
    BLACKLIST = {
        "SPY", "QQQ", "DIA", "IWM", "VIX", "BTC", "ETH", "USDT", "BNB", "XRP",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    }
    STOCK_CHANNELS = [
        "stock_gambles",
        "stockmarket_news",
        "stocksnews",
        "stocktrading",
        "trade_signals",
        "stock_market_chat",
        "wallstreetbets_tg",
    ]

    def __init__(self):
        self.sentiment = VaderSingleton()
        self._client = None
        self._has_credentials = bool(
            settings.telegram_api_id and settings.telegram_api_hash
        )
        self.http_client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot; contact@stradegy.dev)",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        if not self._has_credentials:
            logger.info(
                "Telegram API credentials not configured — scanner will return empty results"
            )
        else:
            logger.info("Telegram scanner initialized")

    async def _ensure_client(self) -> bool:
        if not self._has_credentials:
            return False
        if self._client is not None:
            return True
        try:
            from telethon import TelegramClient

            self._client = TelegramClient(
                "stradegy_telegram_session",
                settings.telegram_api_id,
                settings.telegram_api_hash,
            )
            await self._client.start()
            logger.info("Telethon client connected")
            return True
        except ImportError:
            logger.error("telethon not installed — run: pip install telethon")
            self._has_credentials = False
            return False
        except Exception as e:
            logger.error(f"Failed to connect Telethon client: {e}")
            self._has_credentials = False
            return False

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        return {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}

    async def _fetch_channel_messages(
        self, channel: str, limit: int = 30
    ) -> list[TelegramMention]:
        if not await self._ensure_client():
            return []

        try:
            entity = await self._client.get_entity(channel)
            messages = await self._client.get_messages(entity, limit=min(limit, 50))

            mentions: list[TelegramMention] = []
            for msg in messages:
                if not msg.message:
                    continue

                text = msg.message
                tickers = self.extract_tickers(text)
                if not tickers:
                    continue

                sentiment = self.sentiment.analyze(text[:1000])

                created = msg.date if msg.date else datetime.now(timezone.utc)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)

                views = getattr(msg, "views", 0) or 0
                reactions_count = 0
                if msg.reactions:
                    reactions_count = sum(
                        r.count for r in msg.reactions.results
                    ) if msg.reactions.results else 0

                author = None
                if msg.sender_id:
                    author = str(msg.sender_id)

                for ticker in tickers:
                    mention = TelegramMention(
                        ticker_symbol=ticker,
                        channel_name=channel,
                        message_id=str(msg.id),
                        content=text[:500],
                        created_utc=created,
                        views=views,
                        reactions=reactions_count,
                        sentiment_compound=sentiment["compound"],
                        author=author,
                    )
                    mentions.append(mention)

            return mentions
        except Exception as e:
            logger.warning(f"Error fetching Telegram messages from {channel}: {e}")
            return []

    async def scan_hot(self, limit: int = 50) -> list[TelegramMention]:
        if not self._has_credentials:
            return []

        all_mentions: list[TelegramMention] = []
        per_channel = max(1, limit // len(self.STOCK_CHANNELS))

        for channel in self.STOCK_CHANNELS:
            try:
                mentions = await self._fetch_channel_messages(channel, per_channel)
                all_mentions.extend(mentions)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.warning(f"Error scanning Telegram channel {channel}: {e}")

        logger.info(f"Telegram scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_ticker(self, ticker: str, limit: int = 30) -> list[TelegramMention]:
        if not self._has_credentials:
            return []

        all_mentions: list[TelegramMention] = []
        per_channel = max(1, limit // len(self.STOCK_CHANNELS))

        for channel in self.STOCK_CHANNELS:
            try:
                mentions = await self._fetch_channel_messages(channel, per_channel)
                for m in mentions:
                    if m.ticker_symbol.upper() == ticker.upper():
                        all_mentions.append(m)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.warning(f"Error scanning Telegram for {ticker}: {e}")

        logger.info(f"Telegram ticker scan for {ticker}: {len(all_mentions)} mentions found")
        return all_mentions

    async def close(self):
        if self._client:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting Telethon client: {e}")
            self._client = None
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
