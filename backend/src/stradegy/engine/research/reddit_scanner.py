import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.engine.research.models import RedditMention
from stradegy.engine.research.sentiment import VaderSingleton


class RedditScanner:
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
    SUBREDDITS = [
        "wallstreetbets",
        "stocks",
        "pennystocks",
        "investing",
        "smallstreetbets",
    ]
    API_BASE = "https://www.reddit.com"

    def __init__(self):
        self.sentiment = VaderSingleton()
        self._running = False
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("Reddit scanner initialized (public JSON endpoints)")

    def extract_tickers(self, text: str) -> set[str]:
        if not text:
            return set()
        matches = self.TICKER_PATTERN.findall(text)
        tickers = {m for m in matches if len(m) >= 2 and m not in self.BLACKLIST}
        return tickers

    def _parse_post(self, post_data: dict[str, Any]) -> list[RedditMention]:
        title = post_data.get("title", "")
        selftext = post_data.get("selftext", "")
        text = f"{title} {selftext}"
        tickers = self.extract_tickers(text)
        if not tickers:
            return []

        sentiment = self.sentiment.analyze(text)
        created = datetime.fromtimestamp(
            post_data.get("created_utc", 0), tz=timezone.utc
        )

        mentions = []
        for ticker in tickers:
            mention = RedditMention(
                ticker_symbol=ticker,
                subreddit=post_data.get("subreddit", "unknown"),
                post_id=post_data.get("id", ""),
                post_url=f"https://reddit.com{post_data.get('permalink', '')}",
                title=title[:500],
                created_utc=created,
                score=post_data.get("score", 0),
                num_comments=post_data.get("num_comments", 0),
                upvote_ratio=post_data.get("upvote_ratio", 0.0),
                sentiment_compound=sentiment["compound"],
                mention_count_1h=0,
                mention_count_6h=0,
                mention_count_24h=0,
                velocity_vs_avg=0.0,
                author=post_data.get("author", None),
            )
            mentions.append(mention)
        return mentions

    async def _fetch_subreddit(self, subreddit: str, sort: str, limit: int, retries: int = 0) -> list[dict[str, Any]]:
        url = f"{self.API_BASE}/r/{subreddit}/{sort}.json"
        params = {"limit": min(limit, 100)}
        if sort == "top":
            params["t"] = "week"

        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                posts = [child.get("data", {}) for child in children if child.get("data")]
                logger.info(f"Fetched {len(posts)} posts from r/{subreddit}/{sort}")
                return posts
            elif resp.status_code == 429:
                if retries >= 3:
                    logger.warning(f"Reddit rate limited for r/{subreddit} after {retries} retries. Skipping.")
                    return []
                wait = min(2 ** retries * 5, 30)
                logger.warning(f"Reddit rate limited for r/{subreddit}. Waiting {wait}s...")
                await asyncio.sleep(wait)
                return await self._fetch_subreddit(subreddit, sort, limit, retries + 1)
            elif resp.status_code == 403:
                logger.warning(f"Reddit blocked request for r/{subreddit} (403). User-Agent may be blocked.")
                return []
            else:
                logger.warning(f"Reddit API error {resp.status_code} for r/{subreddit}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.warning(f"Reddit fetch error for r/{subreddit}: {e}")
            return []

    async def scan_recent(self, limit: int = 100) -> list[RedditMention]:
        all_mentions: list[RedditMention] = []
        per_sub = max(1, limit // len(self.SUBREDDITS))

        for subreddit in self.SUBREDDITS:
            try:
                posts = await self._fetch_subreddit(subreddit, "new", per_sub)
                for post in posts:
                    mentions = self._parse_post(post)
                    all_mentions.extend(mentions)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.warning(f"Error scanning r/{subreddit}: {e}")

        logger.info(f"Reddit scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_hot(self, limit: int = 50) -> list[RedditMention]:
        all_mentions: list[RedditMention] = []
        per_sub = max(1, limit // len(self.SUBREDDITS))

        for subreddit in self.SUBREDDITS:
            try:
                posts = await self._fetch_subreddit(subreddit, "hot", per_sub)
                for post in posts:
                    mentions = self._parse_post(post)
                    all_mentions.extend(mentions)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.warning(f"Error scanning r/{subreddit}: {e}")

        logger.info(f"Reddit hot scan complete: {len(all_mentions)} mentions found")
        return all_mentions

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[RedditMention]:
        all_mentions: list[RedditMention] = []
        per_sub = max(1, limit // len(self.SUBREDDITS))
        search_terms = [ticker, f"${ticker}"]

        for subreddit in self.SUBREDDITS:
            try:
                posts = await self._fetch_subreddit(subreddit, "hot", per_sub)
                for post in posts:
                    title = post.get("title", "")
                    selftext = post.get("selftext", "")
                    text = f"{title} {selftext}"
                    if any(term in text.upper() for term in search_terms):
                        mentions = self._parse_post(post)
                        for m in mentions:
                            if m.ticker_symbol.upper() == ticker.upper():
                                all_mentions.append(m)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.warning(f"Error scanning r/{subreddit} for {ticker}: {e}")

        logger.info(f"Reddit ticker scan for {ticker}: {len(all_mentions)} mentions found")
        return all_mentions

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
