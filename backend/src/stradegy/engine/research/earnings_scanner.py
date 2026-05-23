from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import EarningsSignal


class EarningsScanner:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "X-Finnhub-Token": settings.finnhub_api_key,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            },
            timeout=httpx.Timeout(30.0),
        )
        logger.info("Earnings scanner initialized (Finnhub)")

    async def scan_upcoming(self, from_date: str | None = None, to_date: str | None = None) -> list[EarningsSignal]:
        if not from_date:
            from_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not to_date:
            to_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

        url = "https://finnhub.io/api/v1/calendar/earnings"
        params = {"from": from_date, "to": to_date, "token": settings.finnhub_api_key}

        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Earnings calendar API error {resp.status_code}")
                return []
            data = resp.json()
            earnings = data.get("earningsCalendar", [])
            signals = []
            now = datetime.now(timezone.utc)
            for item in earnings:
                try:
                    ticker = item.get("symbol", "")
                    if not ticker:
                        continue
                    report_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    days_until = (report_date - now).days
                    eps_est = item.get("epsEstimate")
                    eps_actual = item.get("epsActual")
                    rev_est = item.get("revenueEstimate")
                    rev_actual = item.get("revenueActual")

                    surprise = None
                    if eps_actual and eps_est and eps_est != 0:
                        surprise = round((eps_actual - eps_est) / abs(eps_est) * 100, 2)

                    signal = EarningsSignal(
                        ticker_symbol=ticker,
                        report_date=report_date,
                        eps_estimate=eps_est,
                        eps_actual=eps_actual,
                        revenue_estimate=rev_est,
                        revenue_actual=rev_actual,
                        surprise_pct=surprise,
                        is_upcoming=days_until >= 0,
                        days_until=days_until,
                    )
                    signals.append(signal)
                except Exception as e:
                    logger.debug(f"Earnings parse error: {e}")
                    continue
            logger.info(f"Earnings calendar: {len(signals)} upcoming reports")
            return signals
        except Exception as e:
            logger.warning(f"Earnings fetch error: {e}")
            return []

    async def scan_ticker(self, ticker: str) -> list[EarningsSignal]:
        from_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
        to_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        url = "https://finnhub.io/api/v1/calendar/earnings"
        params = {"from": from_date, "to": to_date, "symbol": ticker, "token": settings.finnhub_api_key}

        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            earnings = data.get("earningsCalendar", [])
            signals = []
            now = datetime.now(timezone.utc)
            for item in earnings:
                try:
                    report_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    days_until = (report_date - now).days
                    eps_est = item.get("epsEstimate")
                    eps_actual = item.get("epsActual")
                    surprise = None
                    if eps_actual and eps_est and eps_est != 0:
                        surprise = round((eps_actual - eps_est) / abs(eps_est) * 100, 2)

                    signal = EarningsSignal(
                        ticker_symbol=ticker,
                        report_date=report_date,
                        eps_estimate=eps_est,
                        eps_actual=eps_actual,
                        revenue_estimate=item.get("revenueEstimate"),
                        revenue_actual=item.get("revenueActual"),
                        surprise_pct=surprise,
                        is_upcoming=days_until >= 0,
                        days_until=days_until,
                    )
                    signals.append(signal)
                except Exception:
                    continue
            return signals
        except Exception as e:
            logger.warning(f"Earnings ticker error for {ticker}: {e}")
            return []

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
