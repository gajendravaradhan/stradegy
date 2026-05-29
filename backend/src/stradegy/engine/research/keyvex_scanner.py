import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import KeyVexSignal


class KeyVexScanner:
    API_BASE = "https://mcp.keyvex.com"
    TOOLS = {
        "dark_pool": "get_dark_pool_volume",
        "congress_trades": "get_congressional_trades",
        "insider_trades": "get_insider_transactions",
        "institution_holdings": "get_institution_holdings",
        "fails_to_deliver": "get_fails_to_deliver",
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Stradegy/3.1.0 (financial research bot; contact@stradegy.dev) Python-httpx/0.27",
                "Accept": "application/json",
                "X-API-Key": settings.keyvex_api_key,
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        self.api_key = settings.keyvex_api_key
        if not self.api_key:
            logger.info("KeyVex API key not configured — KeyVex scanner will return empty results")
        else:
            logger.info("KeyVex scanner initialized")

    async def _call_tool(self, tool_name: str, params: dict[str, Any], retries: int = 0) -> dict[str, Any] | None:
        url = f"{self.API_BASE}/tools/{tool_name}"
        try:
            resp = await self.client.post(url, json=params)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                if retries >= 3:
                    logger.warning(f"KeyVex rate limited for {tool_name} after {retries} retries. Skipping.")
                    return None
                wait = min(2 ** retries * 2, 20)
                logger.warning(f"KeyVex rate limited for {tool_name}. Waiting {wait}s...")
                await asyncio.sleep(wait)
                return await self._call_tool(tool_name, params, retries + 1)
            elif resp.status_code == 404:
                logger.warning(f"KeyVex tool {tool_name} not found (404)")
                return None
            else:
                logger.warning(f"KeyVex API error {resp.status_code} for {tool_name}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"KeyVex fetch error for {tool_name}: {e}")
            return None

    async def _fetch_dark_pool(self, ticker: str) -> dict[str, Any]:
        result = await self._call_tool(self.TOOLS["dark_pool"], {"symbol": ticker.upper()})
        return result or {}

    async def _fetch_congress_trades(self, ticker: str, limit: int = 5) -> list[dict[str, Any]]:
        result = await self._call_tool(self.TOOLS["congress_trades"], {"symbol": ticker.upper(), "limit": limit})
        if result:
            return result.get("trades", []) or result.get("data", []) or []
        return []

    async def _fetch_insider_trades(self, ticker: str, limit: int = 10) -> list[dict[str, Any]]:
        result = await self._call_tool(self.TOOLS["insider_trades"], {"symbol": ticker.upper(), "limit": limit})
        if result:
            return result.get("transactions", []) or result.get("data", []) or []
        return []

    async def _fetch_institution_holdings(self, ticker: str) -> dict[str, Any]:
        result = await self._call_tool(self.TOOLS["institution_holdings"], {"symbol": ticker.upper()})
        return result or {}

    async def _fetch_fails_to_deliver(self, ticker: str) -> dict[str, Any]:
        result = await self._call_tool(self.TOOLS["fails_to_deliver"], {"symbol": ticker.upper()})
        return result or {}

    def _compute_signal_score(self, combined: dict[str, Any]) -> float:
        score = 0.0

        dp_vol = combined.get("dark_pool_volume", 0)
        if dp_vol > 1_000_000:
            score += 25
        elif dp_vol > 100_000:
            score += 15
        elif dp_vol > 10_000:
            score += 5

        congress_type = combined.get("congressional_trade_type")
        congress_amount = combined.get("congressional_trade_amount", 0) or 0
        if congress_type == "P" or congress_type == "Purchase":
            score += 20
            if congress_amount > 500_000:
                score += 15
            elif congress_amount > 100_000:
                score += 10
        elif congress_type == "S" or congress_type == "Sale":
            score -= 10

        insider_type = combined.get("insider_transaction_type")
        insider_shares = combined.get("insider_shares", 0)
        if insider_type and "P" in str(insider_type).upper():
            score += 15
            if insider_shares > 10_000:
                score += 5
        elif insider_type and "S" in str(insider_type).upper():
            score -= 5

        holding_change = combined.get("institution_holdings_change_pct")
        if holding_change is not None:
            if holding_change > 5:
                score += 10
            elif holding_change < -5:
                score -= 10

        ftd = combined.get("sec_fails_to_deliver", 0)
        if ftd > 100_000:
            score -= 10

        return max(0.0, min(100.0, score))

    async def scan_ticker(self, ticker: str) -> list[KeyVexSignal]:
        if not self.api_key:
            return []
        try:
            dp, congress, insider, holdings, ftd = await asyncio.gather(
                self._fetch_dark_pool(ticker),
                self._fetch_congress_trades(ticker),
                self._fetch_insider_trades(ticker),
                self._fetch_institution_holdings(ticker),
                self._fetch_fails_to_deliver(ticker),
                return_exceptions=True,
            )

            if isinstance(dp, Exception):
                logger.warning(f"KeyVex dark pool failed for {ticker}: {dp}")
                dp = {}
            if isinstance(congress, Exception):
                logger.warning(f"KeyVex congress failed for {ticker}: {congress}")
                congress = []
            if isinstance(insider, Exception):
                logger.warning(f"KeyVex insider failed for {ticker}: {insider}")
                insider = []
            if isinstance(holdings, Exception):
                logger.warning(f"KeyVex holdings failed for {ticker}: {holdings}")
                holdings = {}
            if isinstance(ftd, Exception):
                logger.warning(f"KeyVex FTD failed for {ticker}: {ftd}")
                ftd = {}

            top_congress = congress[0] if congress else {}
            top_insider = insider[0] if insider else {}

            combined = {
                "dark_pool_volume": dp.get("volume", 0) or dp.get("total_volume", 0),
                "dark_pool_trade_count": dp.get("trade_count", 0) or dp.get("trades", 0),
                "congressional_trade_amount": float(top_congress.get("amount", 0) or 0),
                "congressional_trade_type": top_congress.get("transaction_type", "") or top_congress.get("type", ""),
                "congressional_rep_name": top_congress.get("representative", "") or top_congress.get("name", ""),
                "insider_shares": int(top_insider.get("shares", 0) or 0),
                "insider_transaction_type": top_insider.get("transaction_type", "") or top_insider.get("type", ""),
                "institution_holdings_change_pct": holdings.get("change_pct")
                or holdings.get("change_percent"),
                "sec_fails_to_deliver": int(ftd.get("total", 0) or ftd.get("count", 0) or 0),
            }

            signal = KeyVexSignal(
                ticker_symbol=ticker,
                dark_pool_volume=combined["dark_pool_volume"],
                dark_pool_trade_count=combined["dark_pool_trade_count"],
                congressional_trade_amount=combined["congressional_trade_amount"] or None,
                congressional_trade_type=combined["congressional_trade_type"] or None,
                congressional_rep_name=combined["congressional_rep_name"] or None,
                insider_shares=combined["insider_shares"],
                insider_transaction_type=combined["insider_transaction_type"] or None,
                institution_holdings_change_pct=combined["institution_holdings_change_pct"],
                sec_fails_to_deliver=combined["sec_fails_to_deliver"],
                signal_score=self._compute_signal_score(combined),
                report_date=datetime.now(timezone.utc),
            )
            logger.info(f"KeyVex scan for {ticker}: signal_score={signal.signal_score}")
            return [signal]
        except Exception as e:
            logger.warning(f"KeyVex scan error for {ticker}: {e}")
            return []

    async def scan_hot(self, limit: int = 50) -> list[KeyVexSignal]:
        logger.info("KeyVex scan_hot requires specific tickers; returning empty. Use scan_ticker instead.")
        return []

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
