import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings


class PriceMonitor:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=httpx.Timeout(30.0),
        )
        self.alpaca_base_url = settings.alpaca_base_url
        self.alpaca_key = settings.alpaca_api_key
        self.alpaca_secret = settings.alpaca_secret_key

    async def _is_market_open(self) -> bool:
        now = datetime.now(timezone.utc)
        if now.weekday() >= 5:
            return False
        et = now.astimezone(__import__("zoneinfo").ZoneInfo("US/Eastern"))
        market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= et < market_close

    async def fetch_live_quotes(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        if not await self._is_market_open():
            return {}
        quotes = {}
        try:
            for batch in [tickers[i:i + 50] for i in range(0, len(tickers), 50)]:
                symbols = ",".join(batch)
                resp = await self.client.get(
                    f"{self.alpaca_base_url}/v2/stocks/quotes/latest",
                    headers={
                        "APCA-API-KEY-ID": self.alpaca_key,
                        "APCA-API-SECRET-KEY": self.alpaca_secret,
                    },
                    params={"symbols": symbols},
                )
                if resp.status_code == 200:
                    data = resp.json().get("quotes", {})
                    for symbol, quote in data.items():
                        quotes[symbol] = {
                            "bid": quote.get("bp", 0),
                            "ask": quote.get("ap", 0),
                            "bid_size": quote.get("bs", 0),
                            "ask_size": quote.get("as", 0),
                            "timestamp": quote.get("t", ""),
                        }
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"Price monitor fetch error: {e}")
        return quotes

    async def check_price_movements(self, tickers: list[str], thresholds: dict[str, float] | None = None) -> list[dict[str, Any]]:
        alerts = []
        quotes = await self.fetch_live_quotes(tickers)
        for symbol, quote in quotes.items():
            mid = (quote.get("bid", 0) + quote.get("ask", 0)) / 2
            if mid <= 0:
                continue
            threshold = thresholds.get(symbol, 0.05) if thresholds else 0.05
            alerts.append({
                "symbol": symbol,
                "price": mid,
                "threshold": threshold,
                "timestamp": quote.get("timestamp", ""),
            })
        return alerts

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
