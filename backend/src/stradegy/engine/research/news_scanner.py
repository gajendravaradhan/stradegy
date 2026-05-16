from datetime import datetime, timezone
from typing import Any

import finnhub
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import NewsArticle
from stradegy.engine.research.sentiment import FinBertPipeline


class NewsScanner:
    def __init__(self):
        self.sentiment = FinBertPipeline(device="cpu")
        self.client = None
        if settings.finnhub_api_key:
            self.client = finnhub.Client(api_key=settings.finnhub_api_key)
        else:
            logger.info("Finnhub API key not configured — news scanner will return empty results")

    def _ensure_client(self) -> bool:
        return self.client is not None

    async def fetch_news(self, symbol: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._ensure_client():
            return []
        try:
            news = self.client.company_news(
                symbol.upper(),
                _from=(datetime.now(timezone.utc) - __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%d"),
                to=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            return news[:limit] if news else []
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []

    def analyze_article(self, article: dict[str, Any], symbol: str) -> NewsArticle | None:
        headline = article.get("headline", "")
        if not headline:
            return None

        summary = article.get("summary", "")
        text = f"{headline}. {summary}"[:512]
        sentiment = self.sentiment.analyze(text)

        return NewsArticle(
            ticker_symbol=symbol,
            headline=headline[:500],
            article_url=article.get("url", ""),
            source=article.get("source", "unknown"),
            published_at=datetime.fromtimestamp(
                article.get("datetime", 0), tz=timezone.utc
            ),
            finbert_sentiment=sentiment.get("compound", 0.0),
            finbert_confidence=sentiment.get("score", 0.0),
            finbert_label=sentiment.get("label", "neutral"),
        )

    async def scan_ticker(self, symbol: str, limit: int = 20) -> list[NewsArticle]:
        articles = await self.fetch_news(symbol, limit)
        results = []
        for article in articles:
            analyzed = self.analyze_article(article, symbol)
            if analyzed:
                results.append(analyzed)
        return results

    async def aggregate_sentiment(self, symbol: str, limit: int = 20) -> dict[str, Any]:
        articles = await self.scan_ticker(symbol, limit)
        if not articles:
            return {
                "compound": 0.0,
                "label": "neutral",
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 0.0,
                "sample_size": 0,
            }

        compounds = [a.finbert_sentiment for a in articles]
        labels = [a.finbert_label for a in articles]
        avg = sum(compounds) / len(compounds)

        return {
            "compound": avg,
            "label": (
                "positive" if avg > 0.05
                else "negative" if avg < -0.05
                else "neutral"
            ),
            "positive_ratio": labels.count("positive") / len(labels),
            "negative_ratio": labels.count("negative") / len(labels),
            "neutral_ratio": labels.count("neutral") / len(labels),
            "sample_size": len(articles),
            "articles": [
                {
                    "headline": a.headline,
                    "url": a.article_url,
                    "sentiment": a.finbert_sentiment,
                    "label": a.finbert_label,
                }
                for a in articles[:5]
            ],
        }
