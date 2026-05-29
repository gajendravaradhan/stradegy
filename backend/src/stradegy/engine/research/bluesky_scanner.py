import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import BlueskyMention
from stradegy.engine.research.sentiment import VaderSingleton


class BlueskyScanner:
    TICKER_PATTERN = re.compile(r"\$?([A-Z]{1,5})\b")
    BLACKLIST = {
        "SPY", "QQQ", "DIA", "IWM", "VIX", "BTC", "ETH", "USDT", "BNB", "XRP",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    }
    FINANCE_KEYWORDS = [
        "$AAPL", "$TSLA", "$NVDA", "$GME", "$AMC", "$SPY", "$QQQ",
        "stock market", "trading", "bullish", "bearish", "earnings",
        "crypto", "finance", "investing",
    ]
    API_BASE = "https://public.api.bsky.app"

    def __init__(self):
        self.sentiment = VaderSingleton()
        self._atproto_client = None
        self._has_credentials = bool(
            settings.bluesky_handle and settings.bluesky_app_password
        )
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot; contact@stradegy.dev) Python-httpx/0.27",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        if not self._has_credentials:
            logger.info(
                "Bluesky credentials not configured — scanner will return empty results"
            )
        else:
            logger.info("Bluesky scanner initialized")

    async def _ensure_atproto_client(self) -> bool:
        if not self._has_credentials:
            return False
        if self._atproto_client is not None:
            return True
        try:
            from atproto import Client

            self._atproto_client = Client()
            await self._atproto_client.login(
                settings.bluesky_handle, settings.bluesky_app_password
            )
            logger.info("AT Protocol client connected")
            return True
        except ImportError:
            logger.error("atproto not installed — run: pip install atproto")
            self._has_credentials = False
            return False
        except Exception as e:
            logger.error(f"Failed to login to Bluesky: {e}")
            self._has_credentials = False
            return False

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        return {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}

    async def _search_posts(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        url = f"{self.API_BASE}/xrpc/app.bsky.feed.searchPosts"
        params = {"q": query, "limit": min(limit, 100), "sort": "latest"}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("posts", [])
            elif resp.status_code == 429:
                logger.warning(f"Bluesky rate limited for query '{query}'")
                return []
            else:
                logger.warning(
                    f"Bluesky API error {resp.status_code} for '{query}': {resp.text[:200]}"
                )
                return []
        except Exception as e:
            logger.warning(f"Bluesky search error for '{query}': {e}")
            return []

    def _parse_post(self, post: dict[str, Any], ticker: str) -> BlueskyMention | None:
        record = post.get("record", {})
        text = record.get("text", "")
        if not text:
            return None

        sentiment = self.sentiment.analyze(text[:500])

        created = record.get("createdAt")
        if created:
            from dateutil.parser import isoparse
            created_dt = isoparse(created)
        else:
            created_dt = datetime.now(timezone.utc)

        author_info = post.get("author", {})
        author = author_info.get("handle") or author_info.get("displayName")

        post_uri = post.get("uri", "")
        post_id = post_uri.split("/")[-1] if post_uri else str(post.get("cid", ""))
        post_url = f"https://bsky.app/profile/{author_info.get('handle', 'unknown')}/post/{post_id}"

        likes = post.get("likeCount", 0) or 0
        reposts = post.get("repostCount", 0) or 0
        replies = post.get("replyCount", 0) or 0

        return BlueskyMention(
            ticker_symbol=ticker,
            post_id=post_id,
            post_url=post_url,
            content=text[:500],
            created_utc=created_dt,
            likes=likes,
            reposts=reposts,
            replies=replies,
            sentiment_compound=sentiment["compound"],
            author=author,
        )

    async def scan_hot(self, limit: int = 50) -> list[BlueskyMention]:
        all_mentions: list[BlueskyMention] = []
        seen_post_ids: set[str] = set()
        per_keyword = max(1, limit // len(self.FINANCE_KEYWORDS))

        for keyword in self.FINANCE_KEYWORDS:
            try:
                posts = await self._search_posts(keyword, limit=min(per_keyword, 25))
                for post in posts:
                    post_id = str(post.get("uri", post.get("cid", "")))
                    if post_id in seen_post_ids:
                        continue
                    seen_post_ids.add(post_id)

                    record = post.get("record", {})
                    text = record.get("text", "")
                    tickers = self.extract_tickers(text)
                    if not tickers:
                        continue

                    for ticker in tickers:
                        mention = self._parse_post(post, ticker)
                        if mention:
                            all_mentions.append(mention)

                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error scanning Bluesky for '{keyword}': {e}")

        logger.info(f"Bluesky scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_ticker(self, ticker: str, limit: int = 30) -> list[BlueskyMention]:
        all_mentions: list[BlueskyMention] = []
        seen_post_ids: set[str] = set()

        queries = [f"${ticker}", ticker]
        for query in queries:
            try:
                posts = await self._search_posts(query, limit=min(limit, 50))
                for post in posts:
                    post_id = str(post.get("uri", post.get("cid", "")))
                    if post_id in seen_post_ids:
                        continue
                    seen_post_ids.add(post_id)

                    record = post.get("record", {})
                    text = record.get("text", "")
                    tickers_in_text = self.extract_tickers(text)
                    if ticker.upper() not in tickers_in_text:
                        continue

                    mention = self._parse_post(post, ticker)
                    if mention:
                        all_mentions.append(mention)

                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error scanning Bluesky for {ticker}: {e}")

        logger.info(f"Bluesky ticker scan for {ticker}: {len(all_mentions)} mentions found")
        return all_mentions

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
        self._atproto_client = None
