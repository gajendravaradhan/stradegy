import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator

from stradegy.config import settings


class FredIndicator(BaseModel):
    ticker_symbol: str = Field("MARKET", min_length=1, max_length=16)
    indicator_name: str
    series_id: str
    value: float
    unit: str
    last_updated: datetime
    frequency: str = "M"

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FredScanner:
    SERIES = {
        "DGS10": ("10Y Treasury Yield", "percent"),
        "DTWEXBGS": ("DXY Dollar Index", "index"),
        "GDP": ("Gross Domestic Product", "billions_usd"),
        "CPIAUCSL": ("Consumer Price Index", "index"),
    }

    def __init__(self):
        self.client = None
        if settings.fred_api_key:
            try:
                from fredapi import Fred

                self.client = Fred(api_key=settings.fred_api_key)
                logger.info("FRED scanner initialized")
            except ImportError:
                logger.warning("fredapi not installed — FRED scanner will return empty results")
            except Exception as e:
                logger.warning(f"FRED client init failed: {e}")
        else:
            logger.info("FRED API key not configured — scanner will return empty results")

    def _ensure_client(self) -> bool:
        return self.client is not None

    def _fetch_series(self, series_id: str) -> float | None:
        try:
            from fredapi import Fred

            series = self.client.get_series(series_id)
            if series is not None and len(series) > 0:
                latest = series.dropna().iloc[-1]
                return float(latest)
            return None
        except Exception as e:
            logger.warning(f"FRED series {series_id} fetch error: {e}")
            return None

    async def scan_hot(self, limit: int = 50) -> list[FredIndicator]:
        if not self._ensure_client():
            return []

        try:
            indicators = []
            now = datetime.now(timezone.utc)
            for series_id, (name, unit) in self.SERIES.items():
                value = await asyncio.to_thread(self._fetch_series, series_id)
                if value is not None:
                    indicator = FredIndicator(
                        ticker_symbol="MARKET",
                        indicator_name=name,
                        series_id=series_id,
                        value=round(value, 4),
                        unit=unit,
                        last_updated=now,
                    )
                    indicators.append(indicator)
                else:
                    logger.warning(f"FRED: no data for {series_id} ({name})")

            logger.info(f"FRED scan complete: {len(indicators)} indicators fetched")
            return indicators
        except Exception as e:
            logger.error(f"FRED scan failed: {e}")
            return []

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[FredIndicator]:
        return await self.scan_hot(limit=limit)

    async def close(self):
        self.client = None
