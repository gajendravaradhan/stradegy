import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import AdanosSentimentScore


class AdanosScanner:
    ADANOS_API = "https://api.adanos.org/v1"
    SDK_AVAILABLE = False

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.1.0 (financial research bot; contact@stradegy.dev) Python-httpx/0.27",
                "Accept": "application/json",
                "X-API-Key": settings.adanos_api_key,
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        self.api_key = settings.adanos_api_key
        if not self.api_key:
            logger.info("Adanos API key not configured — Adanos scanner will return empty results")
        else:
            self._check_sdk()
            logger.info("Adanos scanner initialized")

    def _check_sdk(self):
        try:
            import social_stock_sentiment  # noqa: F401
            self.SDK_AVAILABLE = True
            logger.info("social-stock-sentiment SDK detected — using native SDK calls")
        except ImportError:
            logger.info("social-stock-sentiment SDK not installed — using REST fallback")
            self.SDK_AVAILABLE = False

    async def _fetch_from_sdk(self, ticker: str) -> dict[str, Any] | None:
        try:
            import social_stock_sentiment
            stock = social_stock_sentiment.Stock(api_key=self.api_key)

            reddit = stock.reddit.trending(days=7, limit=10)
            x_data = stock.x.trending(days=1, limit=10)
            news = stock.news.sentiment(symbol=ticker.upper(), days=3)
            polymarket = None
            try:
                polymarket = stock.polymarket.probability(symbol=ticker.upper())
            except Exception:
                pass

            reddit_items = reddit if isinstance(reddit, list) else reddit.get("data", [])
            x_items = x_data if isinstance(x_data, list) else x_data.get("data", [])
            news_data = news if isinstance(news, dict) else {"sentiment": 0.0, "articles": 0}

            reddit_sent = 0.0
            reddit_count = 0
            for item in reddit_items[:20]:
                sent = item.get("sentiment", item.get("compound", 0.0))
                if isinstance(sent, (int, float)):
                    reddit_sent += float(sent)
                    reddit_count += 1

            x_sent = 0.0
            x_count = 0
            for item in x_items[:20]:
                sent = item.get("sentiment", item.get("compound", 0.0))
                if isinstance(sent, (int, float)):
                    x_sent += float(sent)
                    x_count += 1

            return {
                "reddit_sentiment": round(reddit_sent / max(reddit_count, 1), 4),
                "reddit_mentions": reddit_count,
                "x_sentiment": round(x_sent / max(x_count, 1), 4),
                "x_mentions": x_count,
                "news_sentiment": news_data.get("sentiment", 0.0),
                "news_article_count": news_data.get("articles", news_data.get("count", 0)),
                "polymarket_probability": polymarket.get("probability") if polymarket else None,
            }
        except Exception as e:
            logger.warning(f"Adanos SDK error for {ticker}: {e}")
            return None

    async def _fetch_reddit_sentiment(self, ticker: str, retries: int = 0) -> dict[str, Any]:
        url = f"{self.ADANOS_API}/reddit/trending"
        params = {"symbol": ticker.upper(), "days": 7, "limit": 20}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", []) if isinstance(data, dict) else data
                values = [float(i.get("sentiment", i.get("compound", 0.0))) for i in items[:20]
                     if i.get("sentiment") or i.get("compound")]
                return {
                    "sentiment": round(sum(values) / max(len(values), 1), 4),
                    "mentions": len(items),
                }
            elif resp.status_code == 429:
                if retries >= 3:
                    return {"sentiment": 0.0, "mentions": 0}
                await asyncio.sleep(min(2 ** retries * 2, 20))
                return await self._fetch_reddit_sentiment(ticker, retries + 1)
            return {"sentiment": 0.0, "mentions": 0}
        except Exception:
            return {"sentiment": 0.0, "mentions": 0}

    async def _fetch_x_sentiment(self, ticker: str, retries: int = 0) -> dict[str, Any]:
        url = f"{self.ADANOS_API}/x/trending"
        params = {"symbol": ticker.upper(), "days": 1, "limit": 20}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", []) if isinstance(data, dict) else data
                values = [float(i.get("sentiment", i.get("compound", 0.0))) for i in items[:20]
                     if i.get("sentiment") or i.get("compound")]
                return {
                    "sentiment": round(sum(values) / max(len(values), 1), 4),
                    "mentions": len(items),
                }
            elif resp.status_code == 429:
                if retries >= 3:
                    return {"sentiment": 0.0, "mentions": 0}
                await asyncio.sleep(min(2 ** retries * 2, 20))
                return await self._fetch_x_sentiment(ticker, retries + 1)
            return {"sentiment": 0.0, "mentions": 0}
        except Exception:
            return {"sentiment": 0.0, "mentions": 0}

    async def _fetch_news_sentiment(self, ticker: str, retries: int = 0) -> dict[str, Any]:
        url = f"{self.ADANOS_API}/news/sentiment"
        params = {"symbol": ticker.upper(), "days": 3}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "sentiment": data.get("sentiment", data.get("compound", 0.0)),
                    "articles": data.get("articles", data.get("count", 0)),
                }
            elif resp.status_code == 429:
                if retries >= 3:
                    return {"sentiment": 0.0, "articles": 0}
                await asyncio.sleep(min(2 ** retries * 2, 20))
                return await self._fetch_news_sentiment(ticker, retries + 1)
            return {"sentiment": 0.0, "articles": 0}
        except Exception:
            return {"sentiment": 0.0, "articles": 0}

    async def _fetch_polymarket(self, ticker: str, retries: int = 0) -> float | None:
        url = f"{self.ADANOS_API}/polymarket/probability"
        params = {"symbol": ticker.upper()}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("probability", data.get("prob"))
            elif resp.status_code == 429:
                if retries >= 3:
                    return None
                await asyncio.sleep(min(2 ** retries * 2, 20))
                return await self._fetch_polymarket(ticker, retries + 1)
            return None
        except Exception:
            return None

    async def scan_ticker(self, ticker: str) -> list[AdanosSentimentScore]:
        if not self.api_key:
            return []
        try:
            if self.SDK_AVAILABLE:
                sdk_data = await self._fetch_from_sdk(ticker)
                if sdk_data:
                    reddit_sent = sdk_data.get("reddit_sentiment", 0.0)
                    reddit_mentions = sdk_data.get("reddit_mentions", 0)
                    x_sent = sdk_data.get("x_sentiment", 0.0)
                    x_mentions = sdk_data.get("x_mentions", 0)
                    news_sent = sdk_data.get("news_sentiment", 0.0)
                    news_count = sdk_data.get("news_article_count", 0)
                    poly_prob = sdk_data.get("polymarket_probability")
                else:
                    return []
            else:
                reddit, x, news = await asyncio.gather(
                    self._fetch_reddit_sentiment(ticker),
                    self._fetch_x_sentiment(ticker),
                    self._fetch_news_sentiment(ticker),
                    return_exceptions=True,
                )
                if isinstance(reddit, Exception):
                    reddit = {"sentiment": 0.0, "mentions": 0}
                if isinstance(x, Exception):
                    x = {"sentiment": 0.0, "mentions": 0}
                if isinstance(news, Exception):
                    news = {"sentiment": 0.0, "articles": 0}

                reddit_sent = reddit.get("sentiment", 0.0)
                reddit_mentions = reddit.get("mentions", 0)
                x_sent = x.get("sentiment", 0.0)
                x_mentions = x.get("mentions", 0)
                news_sent = news.get("sentiment", 0.0)
                news_count = news.get("articles", 0)

                poly_prob = await self._fetch_polymarket(ticker)

            total_mentions = reddit_mentions + x_mentions + news_count
            if total_mentions > 0:
                weighted = (
                    reddit_sent * reddit_mentions
                    + x_sent * x_mentions
                    + news_sent * news_count
                ) / total_mentions
            else:
                weighted = 0.0

            confidence = min(1.0, total_mentions / 100)

            if poly_prob is not None and poly_prob > 0 and poly_prob < 1:
                score = round(weighted * 0.7 + (poly_prob - 0.5) * 0.3, 4)
            else:
                score = round(weighted, 4)

            result = AdanosSentimentScore(
                ticker_symbol=ticker,
                reddit_sentiment=reddit_sent,
                reddit_mentions=reddit_mentions,
                x_sentiment=x_sent,
                x_mentions=x_mentions,
                news_sentiment=news_sent,
                news_article_count=news_count,
                polymarket_probability=poly_prob,
                aggregated_score=score,
                aggregated_confidence=confidence,
                fetched_at=datetime.now(timezone.utc),
            )
            logger.info(
                f"Adanos scan for {ticker}: aggregated={result.aggregated_score:.3f}, "
                f"confidence={result.aggregated_confidence:.2f}"
            )
            return [result]
        except Exception as e:
            logger.warning(f"Adanos scan error for {ticker}: {e}")
            return []

    async def scan_hot(self, limit: int = 50) -> list[AdanosSentimentScore]:
        logger.info("Adanos scan_hot requires specific tickers; returning empty. Use scan_ticker instead.")
        return []

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
