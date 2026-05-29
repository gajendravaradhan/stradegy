import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import YouTubeMention
from stradegy.engine.research.sentiment import VaderSingleton


class YouTubeScanner:
    TICKER_PATTERN = re.compile(r"\$?([A-Z]{1,5})\b")
    BLACKLIST = {
        "SPY", "QQQ", "DIA", "IWM", "VIX", "BTC", "ETH", "USDT", "BNB", "XRP",
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL",
    }
    STOCK_SEARCH_QUERIES = [
        "stock market news",
        "trading signals today",
        "best stocks to buy",
        "earnings report analysis",
        "crypto market update",
    ]
    API_BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.sentiment = VaderSingleton()
        self.api_key = settings.youtube_api_key
        self._has_credentials = bool(self.api_key)
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot; contact@stradegy.dev) Python-httpx/0.27",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        if not self._has_credentials:
            logger.info("YouTube API key not configured — scanner will return empty results")
        else:
            logger.info("YouTube scanner initialized")

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        return {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}

    async def _search_videos(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        url = f"{self.API_BASE}/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "relevanceLanguage": "en",
            "key": self.api_key,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("items", [])
            elif resp.status_code == 429:
                logger.warning(f"YouTube rate limited for query '{query}'")
                return []
            elif resp.status_code == 403:
                logger.warning("YouTube API quota exceeded or key invalid")
                return []
            else:
                logger.warning(
                    f"YouTube API error {resp.status_code} for '{query}': {resp.text[:200]}"
                )
                return []
        except Exception as e:
            logger.warning(f"YouTube search error for '{query}': {e}")
            return []

    async def _get_comment_threads(
        self, video_id: str, max_results: int = 20
    ) -> list[dict[str, Any]]:
        url = f"{self.API_BASE}/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "order": "relevance",
            "key": self.api_key,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("items", [])
            elif resp.status_code == 403:
                return []
            elif resp.status_code == 429:
                logger.warning(f"YouTube rate limited for comments on {video_id}")
                return []
            else:
                logger.warning(
                    f"YouTube comments API error {resp.status_code} for {video_id}: {resp.text[:200]}"
                )
                return []
        except Exception as e:
            logger.warning(f"YouTube comments fetch error for {video_id}: {e}")
            return []

    def _parse_comment(
        self, comment_item: dict[str, Any], video_id: str, video_title: str, ticker: str
    ) -> YouTubeMention | None:
        snippet = comment_item.get("snippet", {})
        top_comment = snippet.get("topLevelComment", {}).get("snippet", {})
        text = top_comment.get("textDisplay", "")
        if not text:
            return None

        sentiment = self.sentiment.analyze(text[:500])

        published = top_comment.get("publishedAt")
        if published:
            from dateutil.parser import isoparse
            try:
                published_dt = isoparse(published)
            except Exception:
                published_dt = datetime.now(timezone.utc)
        else:
            published_dt = datetime.now(timezone.utc)

        comment_id = top_comment.get("id", snippet.get("topLevelComment", {}).get("id", ""))
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        likes = top_comment.get("likeCount", 0) or 0
        author = top_comment.get("authorDisplayName")

        return YouTubeMention(
            ticker_symbol=ticker,
            video_id=video_id,
            video_url=video_url,
            comment_id=comment_id,
            comment_text=text[:500],
            created_utc=published_dt,
            likes=likes,
            sentiment_compound=sentiment["compound"],
            author=author,
        )

    async def scan_hot(self, limit: int = 50) -> list[YouTubeMention]:
        if not self._has_credentials:
            return []

        all_mentions: list[YouTubeMention] = []
        seen_comment_ids: set[str] = set()
        seen_video_ids: set[str] = set()

        for query in self.STOCK_SEARCH_QUERIES:
            try:
                videos = await self._search_videos(query, max_results=5)
                for video_item in videos:
                    video_id = video_item.get("id", {}).get("videoId", "")
                    if not video_id or video_id in seen_video_ids:
                        continue
                    seen_video_ids.add(video_id)

                    video_title = (
                        video_item.get("snippet", {}).get("title", "")
                    )

                    comments = await self._get_comment_threads(video_id, max_results=20)
                    for comment_item in comments:
                        comment_id = str(comment_item.get("id", ""))
                        if comment_id in seen_comment_ids:
                            continue
                        seen_comment_ids.add(comment_id)

                        top_comment = (
                            comment_item.get("snippet", {})
                            .get("topLevelComment", {})
                            .get("snippet", {})
                        )
                        text = top_comment.get("textDisplay", "")
                        tickers = self.extract_tickers(text)
                        if not tickers:
                            tickers = self.extract_tickers(video_title)

                        for ticker in tickers:
                            mention = self._parse_comment(
                                comment_item, video_id, video_title, ticker
                            )
                            if mention:
                                all_mentions.append(mention)

                    await asyncio.sleep(0.5)

                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error scanning YouTube for '{query}': {e}")

        logger.info(f"YouTube scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_ticker(self, ticker: str, limit: int = 20) -> list[YouTubeMention]:
        if not self._has_credentials:
            return []

        all_mentions: list[YouTubeMention] = []
        seen_comment_ids: set[str] = set()
        seen_video_ids: set[str] = set()

        queries = [f"{ticker} stock", f"${ticker} stock", f"{ticker} trading"]
        for query in queries:
            try:
                videos = await self._search_videos(query, max_results=3)
                for video_item in videos:
                    video_id = video_item.get("id", {}).get("videoId", "")
                    if not video_id or video_id in seen_video_ids:
                        continue
                    seen_video_ids.add(video_id)

                    video_title = (
                        video_item.get("snippet", {}).get("title", "")
                    )

                    comments = await self._get_comment_threads(video_id, max_results=10)
                    for comment_item in comments:
                        comment_id = str(comment_item.get("id", ""))
                        if comment_id in seen_comment_ids:
                            continue
                        seen_comment_ids.add(comment_id)

                        top_comment = (
                            comment_item.get("snippet", {})
                            .get("topLevelComment", {})
                            .get("snippet", {})
                        )
                        text = top_comment.get("textDisplay", "")
                        if ticker.upper() not in text.upper():
                            continue

                        mention = self._parse_comment(
                            comment_item, video_id, video_title, ticker
                        )
                        if mention:
                            all_mentions.append(mention)

                    await asyncio.sleep(0.5)

                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"Error scanning YouTube for {ticker}: {e}")

        logger.info(f"YouTube ticker scan for {ticker}: {len(all_mentions)} mentions found")
        return all_mentions

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
