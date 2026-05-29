import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import AlpacaNewsArticle
from stradegy.engine.research.sentiment import VaderSingleton


class AlpacaNewsScanner:
    API_BASE = "https://data.alpaca.markets"
    TICKER_PATTERN = None

    def __init__(self):
        self.sentiment = VaderSingleton()
        self.api_key = settings.alpaca_api_key
        self.secret_key = settings.alpaca_secret_key
        self._has_credentials = bool(self.api_key and self.secret_key)
        self.client = httpx.AsyncClient(
            headers={
                "Apca-Api-Key-Id": self.api_key,
                "Apca-Api-Secret-Key": self.secret_key,
                "Accept": "application/json",
                "User-Agent": "Stradegy/3.0.0 (financial research bot; contact@stradegy.dev)",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        if not self._has_credentials:
            logger.info("Alpaca API keys not configured — news scanner will return empty results")
        else:
            logger.info("Alpaca News scanner initialized")

    async def _fetch_news(
        self, symbol: str, limit: int = 10, page_token: str | None = None
    ) -> dict[str, Any]:
        url = f"{self.API_BASE}/v1beta1/news"
        params: dict[str, Any] = {
            "symbols": symbol.upper(),
            "limit": min(limit, 50),
            "sort": "desc",
        }
        if page_token:
            params["page_token"] = page_token

        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                logger.warning(f"Alpaca News rate limited for {symbol}")
                return {}
            else:
                logger.warning(
                    f"Alpaca News API error {resp.status_code} for {symbol}: {resp.text[:200]}"
                )
                return {}
        except Exception as e:
            logger.warning(f"Alpaca News fetch error for {symbol}: {e}")
            return {}

    def _parse_article(self, article: dict[str, Any], symbol: str) -> AlpacaNewsArticle | None:
        headline = article.get("headline", "")
        if not headline:
            return None

        content = article.get("content") or article.get("summary") or ""
        text = f"{headline}. {content}"[:500]
        sentiment = self.sentiment.analyze(text)

        published = article.get("updated_at") or article.get("created_at")
        if published:
            from dateutil.parser import isoparse
            published_dt = isoparse(published)
        else:
            published_dt = datetime.now(timezone.utc)

        tickers_tags = article.get("symbols", [])
        if isinstance(tickers_tags, str):
            tickers_tags = [tickers_tags]

        return AlpacaNewsArticle(
            ticker_symbol=symbol,
            headline=headline[:500],
            article_url=article.get("url", article.get("article_url", "")),
            source=article.get("source", "alpaca"),
            published_at=published_dt,
            sentiment_compound=sentiment["compound"],
            sentiment_label=sentiment["label"],
            tickers_tags=tickers_tags if tickers_tags else [],
            author=article.get("author"),
        )

    async def scan_ticker(self, symbol: str, limit: int = 10) -> list[AlpacaNewsArticle]:
        if not self._has_credentials:
            return []

        results: list[AlpacaNewsArticle] = []
        try:
            data = await self._fetch_news(symbol, limit)
            if not data:
                return []

            articles = data.get("news", [])
            for article in articles:
                parsed = self._parse_article(article, symbol)
                if parsed:
                    results.append(parsed)

            logger.info(f"Alpaca News for {symbol}: {len(results)} articles")
            return results
        except Exception as e:
            logger.warning(f"Alpaca News scan error for {symbol}: {e}")
            return []

    async def scan_hot(self, limit: int = 50) -> list[AlpacaNewsArticle]:
        if not self._has_credentials:
            return []

        results: list[AlpacaNewsArticle] = []
        seen_headlines: set[str] = set()
        try:
            data = await self._fetch_news("", limit=min(limit, 50))
            if not data:
                return results

            articles = data.get("news", [])
            for article in articles:
                symbols = article.get("symbols", [])
                if isinstance(symbols, str):
                    symbols = [symbols]
                if not symbols:
                    continue

                headline = article.get("headline", "")
                if headline in seen_headlines:
                    continue
                seen_headlines.add(headline)

                for sym in symbols:
                    parsed = self._parse_article(article, sym)
                    if parsed:
                        results.append(parsed)

            logger.info(f"Alpaca News hot scan: {len(results)} articles across {len(seen_headlines)} headlines")
            return results
        except Exception as e:
            logger.warning(f"Alpaca News hot scan error: {e}")
            return []

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
