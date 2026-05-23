import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import DiscordMention
from stradegy.engine.research.sentiment import VaderSingleton


class DiscordScanner:
    TICKER_PATTERN = re.compile(r"\$?([A-Z]{1,5})\b")
    BLACKLIST = {
        "SPY", "QQQ", "DIA", "IWM", "VIX", "BTC", "ETH", "USDT", "BNB", "XRP",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
        "BRK", "BRKB", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "BAC",
        "ABBV", "PFE", "KO", "PEP", "WMT", "MRK", "CSCO", "TMO", "ABT", "ACN",
        "COST", "DIS", "DHR", "VZ", "ADBE", "CRM", "NKE", "TXN", "NEE", "PM",
        "RTX", "HON", "UPS", "LOW", "UNP", "IBM", "QCOM", "SPGI", "INTU", "LMT",
        "GS", "CAT", "BLK", "DE", "MDT", "AMT", "GILD", "SBUX", "T", "CVX",
        "XOM", "OXY", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "KMI", "WMB",
    }
    API_BASE = "https://discord.com/api/v10"

    def __init__(self):
        self.sentiment = VaderSingleton()
        self._running = False
        self.token = settings.discord_bot_token
        self.channel_ids = self._parse_ids(settings.discord_channel_ids)
        self.guild_ids = self._parse_ids(settings.discord_guild_ids)
        self.client: httpx.AsyncClient | None = None
        if self.token and self.channel_ids:
            self.client = httpx.AsyncClient(
                headers={"Authorization": f"Bot {self.token}"},
                timeout=httpx.Timeout(30.0),
            )
        else:
            logger.info(
                "Discord bot token or channel IDs not configured — scanner will return empty results"
            )

    def _parse_ids(self, raw: str) -> list[int]:
        if not raw:
            return []
        ids = []
        for part in raw.split(","):
            part = part.strip()
            if part:
                try:
                    ids.append(int(part))
                except ValueError:
                    logger.warning(f"Invalid Discord ID in config: {part}")
        return ids

    def _ensure_client(self) -> bool:
        return self.client is not None

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        tickers = {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}
        return tickers

    def _build_message_url(self, guild_id: str, channel_id: str, message_id: str) -> str:
        return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    def _analyze_message(self, msg: dict[str, Any], channel: dict[str, Any]) -> list[DiscordMention]:
        content = msg.get("content", "")
        embeds = msg.get("embeds", [])
        for embed in embeds:
            if embed.get("title"):
                content += f" {embed['title']}"
            if embed.get("description"):
                content += f" {embed['description']}"

        tickers = self.extract_tickers(content)
        if not tickers:
            return []

        sentiment = self.sentiment.analyze(content)
        created = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
        guild_id = str(msg.get("guild_id", "0"))
        channel_id = str(msg.get("channel_id", channel.get("id", "0")))
        message_id = str(msg["id"])
        author = msg.get("author", {})
        author_name = author.get("username") if author else None
        reactions = msg.get("reactions", [])
        num_reactions = sum(r.get("count", 0) for r in reactions)
        reply_count = msg.get("reply_count", 0)
        score = msg.get("flags", 0) + num_reactions

        mentions = []
        for ticker in tickers:
            mention = DiscordMention(
                ticker_symbol=ticker,
                guild_id=guild_id,
                channel_id=channel_id,
                channel_name=channel.get("name", "unknown"),
                message_id=message_id,
                message_url=self._build_message_url(guild_id, channel_id, message_id),
                content=content[:1900],
                created_utc=created,
                score=score,
                num_reactions=num_reactions,
                reply_count=reply_count,
                sentiment_compound=sentiment["compound"],
                mention_count_1h=0,
                mention_count_6h=0,
                mention_count_24h=0,
                velocity_vs_avg=0.0,
                author=author_name,
            )
            mentions.append(mention)
        return mentions

    async def _fetch_channel_messages(
        self, channel_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        if not self.client:
            return []
        url = f"{self.API_BASE}/channels/{channel_id}/messages"
        params = {"limit": min(limit, 100)}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for msg in data:
                    msg["channel_id"] = str(channel_id)
                return data
            elif resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 5)
                logger.warning(f"Discord rate limited. Retrying after {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._fetch_channel_messages(channel_id, limit)
            else:
                logger.warning(f"Discord API error {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.warning(f"Discord fetch error for channel {channel_id}: {e}")
            return []

    async def scan_recent(self, limit: int = 100) -> list[DiscordMention]:
        if not self._ensure_client():
            return []

        all_mentions: list[DiscordMention] = []
        per_channel_limit = max(1, limit // len(self.channel_ids)) if self.channel_ids else limit

        for channel_id in self.channel_ids:
            try:
                messages = await self._fetch_channel_messages(channel_id, per_channel_limit)
                if not messages:
                    continue

                channel_info = {"id": str(channel_id), "name": "unknown"}
                for msg in messages:
                    msg_mentions = self._analyze_message(msg, channel_info)
                    all_mentions.extend(msg_mentions)

                await asyncio.sleep(1.1)
            except Exception as e:
                logger.warning(f"Discord scan error for channel {channel_id}: {e}")

        logger.info(f"Discord scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_hot(self, limit: int = 50) -> list[DiscordMention]:
        return await self.scan_recent(limit=limit)

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[DiscordMention]:
        if not self._ensure_client():
            return []

        all_mentions: list[DiscordMention] = []
        search_terms = [ticker, f"${ticker}"]
        per_channel_limit = max(1, limit // len(self.channel_ids)) if self.channel_ids else limit

        for channel_id in self.channel_ids:
            try:
                messages = await self._fetch_channel_messages(channel_id, per_channel_limit)
                if not messages:
                    continue

                channel_info = {"id": str(channel_id), "name": "unknown"}
                for msg in messages:
                    content = msg.get("content", "")
                    if any(term in content.upper() for term in search_terms):
                        msg_mentions = self._analyze_message(msg, channel_info)
                        for m in msg_mentions:
                            if m.ticker_symbol.upper() == ticker.upper():
                                all_mentions.append(m)

                await asyncio.sleep(1.1)
            except Exception as e:
                logger.warning(f"Discord ticker scan error for {ticker} in channel {channel_id}: {e}")

        logger.info(f"Discord ticker scan for {ticker}: {len(all_mentions)} mentions found")
        return all_mentions

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
