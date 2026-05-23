from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from stradegy.engine.research.models import TrendsSignal


class GoogleTrendsScanner:
    INTEREST_OVER_TIME_URL = "https://trends.googleapis.com/trends/api/explore"
    COMPARED_GEO_URL = "https://trends.googleapis.com/trends/api/widgetdata/comparedgeo"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("Google Trends scanner initialized")

    async def scan_ticker(self, ticker: str) -> TrendsSignal | None:
        search_term = f"${ticker} stock"
        try:
            token = await self._get_token(search_term)
            if not token:
                return None
            data = await self._fetch_interest_over_time(token, search_term)
            if not data:
                return None
            return self._parse_trends_data(ticker, data)
        except Exception as e:
            logger.warning(f"Google Trends error for {ticker}: {e}")
            return None

    async def _get_token(self, term: str) -> str | None:
        url = "https://trends.google.com/trends/api/explore"
        params = {
            "hl": "en-US",
            "tz": "-240",
            "req": f'{{"comparisonItem":[{{"keyword":"{term}","geo":"","time":"today 3-m"}}],"category":0,"property":""}}',
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                return None
            text = resp.text
            if text.startswith(")]}'"):
                text = text[5:]
            data = __import__("json").loads(text)
            widgets = data.get("widgets", [])
            for w in widgets:
                if w.get("id") == "TIMESERIES":
                    return w.get("token")
            return None
        except Exception:
            return None

    async def _fetch_interest_over_time(self, token: str, term: str) -> dict[str, Any] | None:
        url = "https://trends.google.com/trends/api/widgetdata/multiline"
        params = {
            "hl": "en-US",
            "tz": "-240",
            "req": f'{{"time":"today 3-m","resolution":"WEEK","locale":"en-US","comparisonItem":[{{"geo":{{}},"complexKeywordsRestriction":{{"keyword":[{{"type":"BROAD","value":"{term}"}}]}}}}],"requestOptions":{{"property":"","backend":"IZG","category":0}},"userConfig":{{"userType":"USER_TYPE_LEGIT_USER"}}}}',
            "token": token,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                return None
            text = resp.text
            if text.startswith(")]}'"):
                text = text[5:]
            return __import__("json").loads(text)
        except Exception:
            return None

    def _parse_trends_data(self, ticker: str, data: dict[str, Any]) -> TrendsSignal:
        timeline_data = data.get("timelineData", [])
        if not timeline_data:
            return TrendsSignal(
                ticker_symbol=ticker,
                interest_score=0.0,
                interest_vs_90d_avg=0.0,
                direction="flat",
            )

        values = []
        for point in timeline_data:
            val_str = point.get("value", ["0"])
            if isinstance(val_str, list) and val_str:
                try:
                    values.append(float(val_str[0]))
                except (ValueError, IndexError):
                    continue

        if not values:
            return TrendsSignal(
                ticker_symbol=ticker,
                interest_score=0.0,
                interest_vs_90d_avg=0.0,
                direction="flat",
            )

        current = values[-1]
        avg = sum(values) / len(values)
        vs_avg = (current - avg) / avg if avg > 0 else 0.0

        if len(values) >= 4:
            recent = sum(values[-4:]) / 4
            older = sum(values[:-4]) / max(len(values) - 4, 1)
            if recent > older * 1.2:
                direction = "up"
            elif recent < older * 0.8:
                direction = "down"
            else:
                direction = "flat"
        else:
            direction = "flat"

        return TrendsSignal(
            ticker_symbol=ticker,
            interest_score=min(current, 100.0),
            interest_vs_90d_avg=round(vs_avg, 2),
            direction=direction,
        )

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
