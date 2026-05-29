import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.engine.research.models import HackerNewsMention
from stradegy.engine.research.sentiment import VaderSingleton


class HackerNewsScanner:
    TICKER_PATTERN = re.compile(r"\$?([A-Z]{1,5})\b")
    BLACKLIST = {
        "SPY", "QQQ", "DIA", "IWM", "VIX", "BTC", "ETH", "USDT", "BNB", "XRP",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    }
    TECH_KEYWORDS = [
        "stock", "trading", "market", "invest", "fintech", "broker",
        "portfolio", "dividend", "etf", "crypto", "trade", "finance",
        "IPO", "SPAC", "acquire", "revenue", "earnings", "stocks",
    ]
    API_BASE = "http://hn.algolia.com/api/v1"

    def __init__(self):
        self.sentiment = VaderSingleton()
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot; contact@stradegy.dev) Python-httpx/0.27",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("HackerNews scanner initialized (public API, no auth)")

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        return {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}

    async def _fetch_stories(
        self, query: str, tags: str = "story", limit: int = 30, page: int = 0
    ) -> list[dict[str, Any]]:
        url = f"{self.API_BASE}/search"
        params = {
            "query": query,
            "tags": tags,
            "hitsPerPage": min(limit, 50),
            "page": page,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("hits", [])
            elif resp.status_code == 429:
                logger.warning("HackerNews Algolia rate limited")
                return []
            else:
                logger.warning(f"HackerNews API error {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.warning(f"HackerNews fetch error: {e}")
            return []

    def _parse_story(self, story: dict[str, Any], ticker: str) -> HackerNewsMention | None:
        title = story.get("title", "")
        if not title:
            return None

        text = title
        story_text = story.get("story_text") or story.get("comment_text") or ""
        if story_text:
            text = f"{title}. {story_text}"[:500]

        sentiment = self.sentiment.analyze(text)

        created = story.get("created_at")
        if created:
            from dateutil.parser import isoparse
            created_dt = isoparse(created)
        else:
            created_dt = datetime.now(timezone.utc)

        story_id = str(story.get("objectID", ""))
        story_url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"

        return HackerNewsMention(
            ticker_symbol=ticker,
            story_id=story_id,
            story_url=story_url,
            title=title[:500],
            created_utc=created_dt,
            points=story.get("points", 0),
            num_comments=story.get("num_comments", 0),
            sentiment_compound=sentiment["compound"],
            author=story.get("author"),
        )

    async def scan_hot(self, limit: int = 50) -> list[HackerNewsMention]:
        all_mentions: list[HackerNewsMention] = []
        seen_ids: set[str] = set()

        for keyword in self.TECH_KEYWORDS[:8]:
            try:
                stories = await self._fetch_stories(keyword, limit=min(30, limit // 4))
                for story in stories:
                    story_id = str(story.get("objectID", ""))
                    if story_id in seen_ids:
                        continue
                    seen_ids.add(story_id)

                    title = story.get("title", "")
                    story_text = story.get("story_text") or story.get("comment_text") or ""
                    text = f"{title} {story_text}"
                    tickers = self.extract_tickers(text)

                    for ticker in tickers:
                        mention = self._parse_story(story, ticker)
                        if mention:
                            all_mentions.append(mention)

                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error scanning HackerNews for '{keyword}': {e}")

        logger.info(f"HackerNews scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_ticker(self, ticker: str, limit: int = 30) -> list[HackerNewsMention]:
        all_mentions: list[HackerNewsMention] = []
        seen_ids: set[str] = set()

        search_terms = [ticker, f"${ticker}"]
        for term in search_terms:
            try:
                stories = await self._fetch_stories(term, limit=min(limit, 50))
                for story in stories:
                    story_id = str(story.get("objectID", ""))
                    if story_id in seen_ids:
                        continue
                    seen_ids.add(story_id)

                    title = story.get("title", "")
                    story_text = story.get("story_text") or story.get("comment_text") or ""
                    text = f"{title} {story_text}"

                    mentions = []
                    tickers_in_text = self.extract_tickers(text)
                    if ticker.upper() in tickers_in_text:
                        mention = self._parse_story(story, ticker)
                        if mention:
                            all_mentions.append(mention)

                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error scanning HackerNews for {ticker}: {e}")

        logger.info(f"HackerNews ticker scan for {ticker}: {len(all_mentions)} mentions found")
        return all_mentions

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
