import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from stradegy.config import settings


class ExtendedHoursQuote(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    regular_price: float | None = None
    previous_close: float | None = None
    pre_market_price: float | None = None
    pre_market_change_pct: float | None = None
    post_market_price: float | None = None
    post_market_change_pct: float | None = None
    market_state: str = "closed"
    created_utc: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class TwelveDataScanner:
    BASE_URL = "https://api.twelvedata.com"

    def __init__(self):
        self._api_key = settings.twelve_data_api_key
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.0.0 (financial research bot)",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        if self._api_key:
            logger.info("Twelve Data scanner initialized")
        else:
            logger.info("Twelve Data API key not configured — scanner will return empty results")

    def _ensure_key(self) -> bool:
        return bool(self._api_key)

    async def _fetch_quote(self, ticker: str, retries: int = 0) -> dict[str, Any] | None:
        url = f"{self.BASE_URL}/quote"
        params = {
            "symbol": ticker,
            "apikey": self._api_key,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "error" or data.get("code") == 400:
                    logger.warning(f"Twelve Data quote error for {ticker}: {data.get('message', 'unknown')}")
                    return None
                return data
            elif resp.status_code == 429:
                if retries >= 3:
                    logger.warning(f"Twelve Data rate limited for {ticker} after 3 retries")
                    return None
                wait = min(2**retries * 5, 30)
                logger.warning(f"Twelve Data rate limited, waiting {wait}s...")
                await asyncio.sleep(wait)
                return await self._fetch_quote(ticker, retries + 1)
            else:
                logger.warning(f"Twelve Data API error {resp.status_code} for {ticker}")
                return None
        except Exception as e:
            logger.warning(f"Twelve Data fetch error for {ticker}: {e}")
            return None

    def _parse_quote(self, ticker: str, data: dict[str, Any]) -> ExtendedHoursQuote | None:
        try:
            def float_or_none(val):
                if val is None:
                    return None
                try:
                    f = float(val)
                    return None if f == 0.0 else round(f, 4)
                except (ValueError, TypeError):
                    return None

            return ExtendedHoursQuote(
                ticker_symbol=ticker,
                regular_price=float_or_none(data.get("close")),
                previous_close=float_or_none(data.get("previous_close")),
                pre_market_price=float_or_none(data.get("pre_market_price")),
                pre_market_change_pct=float_or_none(data.get("pre_market_change_percent")),
                post_market_price=float_or_none(data.get("post_market_price")),
                post_market_change_pct=float_or_none(data.get("post_market_change_percent")),
                market_state=data.get("market_state", "closed"),
                created_utc=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.debug(f"Twelve Data parse error for {ticker}: {e}")
            return None

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[ExtendedHoursQuote]:
        if not self._ensure_key():
            return []

        try:
            data = await self._fetch_quote(ticker)
            if not data:
                return []

            quote = self._parse_quote(ticker, data)
            if quote:
                logger.info(f"Twelve Data quote for {ticker}: market_state={quote.market_state}")
                return [quote]
            return []
        except Exception as e:
            logger.warning(f"Twelve Data scan error for {ticker}: {e}")
            return []

    async def scan_tickers(self, tickers: list[str], limit: int = 50) -> list[ExtendedHoursQuote]:
        if not self._ensure_key():
            return []

        all_quotes: list[ExtendedHoursQuote] = []
        for ticker in tickers:
            quotes = await self.scan_ticker(ticker, limit)
            all_quotes.extend(quotes)
            await asyncio.sleep(1.0)

        logger.info(f"Twelve Data batch scan: {len(all_quotes)} quotes across {len(tickers)} tickers")
        return all_quotes

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
