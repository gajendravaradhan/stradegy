import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.engine.research.models import FINRAShortInterest


class FINRAScanner:
    API_URL = "https://api.finra.org/data/group/otcMarket/name/EquityShortInterest"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.1.0 (financial research bot; contact@stradegy.dev) Python-httpx/0.27",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("FINRA scanner initialized (no auth required)")

    async def _fetch_short_interest(self, settlement_date: str, retries: int = 0) -> list[dict[str, Any]]:
        body = {
            "compareFilters": [
                {
                    "compareType": "EQUAL",
                    "fieldName": "settlementDate",
                    "fieldValue": settlement_date,
                }
            ],
            "limit": 5000,
        }
        try:
            resp = await self.client.post(self.API_URL, json=body)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                if retries >= 3:
                    logger.warning(f"FINRA rate limited after {retries} retries. Skipping.")
                    return []
                wait = min(2 ** retries * 2, 20)
                logger.warning(f"FINRA rate limited. Waiting {wait}s...")
                await asyncio.sleep(wait)
                return await self._fetch_short_interest(settlement_date, retries + 1)
            else:
                logger.warning(f"FINRA API error {resp.status_code}: {resp.text[:200]}")
                return []
        except Exception as e:
            logger.warning(f"FINRA fetch error: {e}")
            return []

    async def _fetch_daily_short_sale(self, date_str: str, retries: int = 0) -> list[dict[str, Any]]:
        url = "https://api.finra.org/data/group/otcMarket/name/DailyShortSaleVolume"
        body = {
            "compareFilters": [
                {
                    "compareType": "EQUAL",
                    "fieldName": "tradeDate",
                    "fieldValue": date_str,
                }
            ],
            "limit": 5000,
        }
        try:
            resp = await self.client.post(url, json=body)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                if retries >= 3:
                    return []
                wait = min(2 ** retries * 2, 20)
                await asyncio.sleep(wait)
                return await self._fetch_daily_short_sale(date_str, retries + 1)
            else:
                return []
        except Exception:
            return []

    def _parse_record(self, record: dict[str, Any]) -> FINRAShortInterest | None:
        try:
            ticker = record.get("symbolCode", "") or record.get("ticker", "")
            if not ticker or len(ticker) > 6:
                return None
            ticker = ticker.upper()

            settlement_str = record.get("settlementDate", "")
            if settlement_str:
                settlement_date = datetime.strptime(settlement_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                settlement_date = datetime.now(timezone.utc)

            short_interest = int(record.get("shortInterestQuantity", 0) or 0)
            avg_volume = int(record.get("averageDailyVolume", 0) or 0)

            days_to_cover = None
            if avg_volume > 0:
                days_to_cover = round(short_interest / avg_volume, 2)

            short_ratio = None
            if short_interest > 0 and avg_volume > 0:
                short_ratio = round(short_interest / avg_volume, 2)

            return FINRAShortInterest(
                ticker_symbol=ticker,
                settlement_date=settlement_date,
                short_interest=short_interest,
                average_daily_volume=avg_volume,
                days_to_cover=days_to_cover,
                short_interest_ratio=short_ratio,
            )
        except Exception as e:
            logger.debug(f"FINRA parse error: {e}")
            return None

    async def scan_hot(self, limit: int = 50) -> list[FINRAShortInterest]:
        settlement_date = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
        try:
            records = await self._fetch_short_interest(settlement_date)
            results = []
            for record in records[:limit]:
                parsed = self._parse_record(record)
                if parsed:
                    results.append(parsed)
            logger.info(f"FINRA scan complete: {len(results)} short interest records")
            return results
        except Exception as e:
            logger.warning(f"FINRA scan error: {e}")
            return []

    async def scan_ticker(self, ticker: str, limit: int = 10) -> list[FINRAShortInterest]:
        settlement_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        try:
            body = {
                "compareFilters": [
                    {
                        "compareType": "EQUAL",
                        "fieldName": "settlementDate",
                        "fieldValue": settlement_date,
                    },
                    {
                        "compareType": "EQUAL",
                        "fieldName": "symbolCode",
                        "fieldValue": ticker.upper(),
                    },
                ],
                "limit": limit,
            }
            resp = await self.client.post(self.API_URL, json=body)
            if resp.status_code != 200:
                return []
            records = resp.json()
            results = []
            for record in records:
                parsed = self._parse_record(record)
                if parsed:
                    results.append(parsed)
            logger.info(f"FINRA ticker scan for {ticker}: {len(results)} records")
            return results
        except Exception as e:
            logger.warning(f"FINRA ticker scan error for {ticker}: {e}")
            return []

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
