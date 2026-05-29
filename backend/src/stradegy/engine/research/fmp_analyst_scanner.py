import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from stradegy.config import settings


class FMPAnalystSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    analyst_company: str
    action: str
    new_grade: str | None = None
    previous_grade: str | None = None
    price_target: float | None = None
    change_date: datetime
    created_utc: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FMPAnalystScanner:
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self):
        self._api_key = settings.fmp_api_key
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot)",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        if self._api_key:
            logger.info("FMP Analyst scanner initialized")
        else:
            logger.info("FMP API key not configured — analyst scanner will return empty results")

    def _ensure_key(self) -> bool:
        return bool(self._api_key)

    async def _fetch_grades(self, ticker: str, limit: int = 20) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/grade/{ticker.upper()}"
        params = {"apikey": self._api_key, "limit": limit}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                logger.warning(f"FMP rate limited for {ticker}")
                return []
            else:
                logger.warning(f"FMP API error {resp.status_code} for {ticker}")
                return []
        except Exception as e:
            logger.warning(f"FMP fetch error for {ticker}: {e}")
            return []

    async def _fetch_upgrades_downgrades(self, ticker: str) -> list[dict[str, Any]]:
        url = f"{self.BASE_URL}/upgrades-downgrades"
        params = {"symbol": ticker.upper(), "apikey": self._api_key}
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.warning(f"FMP upgrades/downgrades error for {ticker}: {e}")
            return []

    def _parse_grade(self, ticker: str, item: dict[str, Any]) -> FMPAnalystSignal | None:
        action = item.get("action", item.get("newGrade", ""))
        if not action:
            return None

        change_date_str = item.get("date", item.get("gradingDate", ""))
        try:
            change_date = datetime.fromisoformat(change_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            change_date = datetime.now(timezone.utc)

        return FMPAnalystSignal(
            ticker_symbol=ticker,
            analyst_company=item.get("gradingCompany", item.get("analyst", "unknown")),
            action=action,
            new_grade=item.get("newGrade"),
            previous_grade=item.get("previousGrade"),
            price_target=item.get("priceTarget") if item.get("priceTarget") else None,
            change_date=change_date,
            created_utc=datetime.now(timezone.utc),
        )

    async def scan_hot(self, limit: int = 50) -> list[FMPAnalystSignal]:
        if not self._ensure_key():
            return []
        queries = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "TSLA"]
        all_signals: list[FMPAnalystSignal] = []
        seen = set()

        for ticker in queries:
            try:
                items = await self._fetch_grades(ticker, limit=limit // len(queries) + 1)
                for item in items:
                    signal = self._parse_grade(ticker, item)
                    if signal:
                        key = f"{ticker}:{signal.analyst_company}:{signal.change_date}"
                        if key not in seen:
                            seen.add(key)
                            all_signals.append(signal)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"FMP scan error for {ticker}: {e}")

        logger.info(f"FMP Analyst scan: {len(all_signals)} grades")
        return all_signals[:limit]

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[FMPAnalystSignal]:
        if not self._ensure_key():
            return []
        try:
            items = await self._fetch_grades(ticker, limit=limit)
            signals = []
            for item in items:
                signal = self._parse_grade(ticker, item)
                if signal:
                    signals.append(signal)
            logger.info(f"FMP Analyst scan for {ticker}: {len(signals)} grades")
            return signals
        except Exception as e:
            logger.warning(f"FMP Analyst scan error for {ticker}: {e}")
            return []

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
