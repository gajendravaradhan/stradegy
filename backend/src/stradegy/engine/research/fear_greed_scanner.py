import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field, field_validator


class FearGreedSignal(BaseModel):
    ticker_symbol: str = Field("MARKET", min_length=1, max_length=16)
    score: int = Field(..., ge=0, le=100)
    rating: str
    created_utc: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FearGreedScanner:
    URL = "https://feargreedchart.com/?action=stock"

    FEAR_GREED_PATTERN = re.compile(r'"fear_greed_display"\s*:\s*"(\d+)"')
    RATING_PATTERN = re.compile(r'"fear_greed_rating"\s*:\s*"([^"]+)"')

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot)",
                "Accept": "application/json, text/html, */*",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("Fear & Greed scanner initialized")

    def _parse_score(self, html: str) -> tuple[int, str] | None:
        score_match = self.FEAR_GREED_PATTERN.search(html)
        if not score_match:
            logger.warning("Fear & Greed: could not extract score from response")
            return None

        try:
            score = int(score_match.group(1))
        except ValueError:
            logger.warning("Fear & Greed: invalid score value")
            return None

        rating_match = self.RATING_PATTERN.search(html)
        rating = rating_match.group(1) if rating_match else self._rating_from_score(score)

        return score, rating

    def _rating_from_score(self, score: int) -> str:
        if score <= 25:
            return "Extreme Fear"
        elif score <= 45:
            return "Fear"
        elif score <= 55:
            return "Neutral"
        elif score <= 75:
            return "Greed"
        else:
            return "Extreme Greed"

    async def _fetch_raw(self, retries: int = 0) -> str | None:
        try:
            resp = await self.client.get(self.URL)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                if retries >= 3:
                    logger.warning("Fear & Greed: rate limited after 3 retries")
                    return None
                wait = min(2**retries * 5, 30)
                logger.warning(f"Fear & Greed: rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
                return await self._fetch_raw(retries + 1)
            else:
                logger.warning(f"Fear & Greed API error {resp.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Fear & Greed fetch error: {e}")
            return None

    async def scan_hot(self, limit: int = 50) -> list[FearGreedSignal]:
        try:
            html = await self._fetch_raw()
            if not html:
                return []

            parsed = self._parse_score(html)
            if not parsed:
                return []

            score, rating = parsed
            signal = FearGreedSignal(
                ticker_symbol="MARKET",
                score=score,
                rating=rating,
                created_utc=datetime.now(timezone.utc),
            )
            logger.info(f"Fear & Greed scan: score={score}, rating={rating}")
            return [signal]
        except Exception as e:
            logger.error(f"Fear & Greed scan failed: {e}")
            return []

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[FearGreedSignal]:
        return await self.scan_hot(limit=limit)

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
