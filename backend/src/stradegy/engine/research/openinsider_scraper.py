import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from stradegy.engine.research.models import InsiderSignal


class OpenInsiderScraper:
    BASE_URL = "http://openinsider.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=self.HEADERS,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        logger.info("OpenInsider scraper initialized")

    async def scan_recent(self, days: int = 7) -> list[InsiderSignal]:
        url = f"{self.BASE_URL}/screener"
        params = {
            "s": "",
            "o": "",
            "pl": "",
            "ph": "",
            "ll": "",
            "lh": "",
            "fd": days,
            "fdr": "",
            "td": 0,
            "tdr": "",
            "fdlyl": "",
            "fdlyh": "",
            "daysago": "",
            "xp": 1,
            "vl": 1,
            "cl": 1,
            "opr": "%250",
            "sw": 50,
            "ow": 1,
            "rw": 1,
            "vw": 1,
            "tw": 1,
            "vip": 1,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"OpenInsider screener error {resp.status_code}")
                return []
            return self._parse_table(resp.text)
        except Exception as e:
            logger.warning(f"OpenInsider fetch error: {e}")
            return []

    async def scan_ticker(self, ticker: str, days: int = 30) -> list[InsiderSignal]:
        url = f"{self.BASE_URL}/screener"
        params = {
            "s": ticker,
            "o": "",
            "pl": "",
            "ph": "",
            "ll": "",
            "lh": "",
            "fd": days,
            "fdr": "",
            "td": 0,
            "tdr": "",
            "fdlyl": "",
            "fdlyh": "",
            "daysago": "",
            "xp": 1,
            "vl": 1,
            "cl": 1,
            "opr": "%250",
            "sw": 50,
            "ow": 1,
            "rw": 1,
            "vw": 1,
            "tw": 1,
            "vip": 1,
        }
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code != 200:
                return []
            signals = self._parse_table(resp.text)
            by_ticker = [s for s in signals if s.ticker_symbol.upper() == ticker.upper()]
            return by_ticker
        except Exception as e:
            logger.warning(f"OpenInsider ticker error for {ticker}: {e}")
            return []

    def _parse_table(self, html: str) -> list[InsiderSignal]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        data_table = None
        for t in tables:
            rows = t.find_all("tr")
            if len(rows) > 50:
                first_data = rows[1] if rows[0].find_all("th") else rows[0]
                cells = first_data.find_all("td")
                if len(cells) >= 10:
                    data_table = t
                    break
        if not data_table:
            logger.warning("OpenInsider: no data table found in response")
            return []

        rows = data_table.find_all("tr")
        start_idx = 1 if rows[0].find_all("th") else 0
        signals = []
        for row in rows[start_idx:]:
            cells = row.find_all("td")
            if len(cells) < 12:
                continue
            try:
                date_str = cells[2].get_text(strip=True)
                if not date_str or len(date_str) != 10:
                    continue
                ticker = cells[3].get_text(strip=True)
                if not ticker or len(ticker) > 6:
                    continue
                insider_name = cells[5].get_text(strip=True)
                insider_title = cells[6].get_text(strip=True)
                trans_type = cells[7].get_text(strip=True)
                price_str = cells[8].get_text(strip=True).replace("$", "").replace(",", "")
                price = float(price_str) if price_str else 0.0
                shares_str = cells[9].get_text(strip=True).replace(",", "").replace("+", "").replace("-", "")
                shares = int(shares_str) if shares_str.isdigit() else 0
                total_value = round(shares * price, 2)
                trans_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                filing_link = cells[11].find("a") if len(cells) > 11 else None
                filing_url = filing_link["href"] if filing_link else ""
                if filing_url and not filing_url.startswith("http"):
                    filing_url = f"{self.BASE_URL}{filing_url}"

                signal = InsiderSignal(
                    ticker_symbol=ticker,
                    insider_name=insider_name,
                    insider_title=insider_title,
                    transaction_date=trans_date,
                    transaction_type=trans_type,
                    shares=shares,
                    price=price,
                    total_value=total_value,
                    filing_url=filing_url,
                )
                signals.append(signal)
            except Exception as e:
                logger.debug(f"OpenInsider parse row error: {e}")
                continue

        cluster_signals = self._detect_clusters(signals)
        clusters = len([s for s in cluster_signals if s.is_cluster])
        logger.info(f"OpenInsider: {len(signals)} transactions, {clusters} clusters")
        return cluster_signals

    def _detect_clusters(self, signals: list[InsiderSignal]) -> list[InsiderSignal]:
        from collections import defaultdict
        ticker_map: dict[str, list[InsiderSignal]] = defaultdict(list)
        for s in signals:
            if s.transaction_type in ("P - Purchase", "P"):
                ticker_map[s.ticker_symbol].append(s)

        result = []
        for ticker, buys in ticker_map.items():
            is_cluster = len(buys) >= 3
            for s in buys:
                s.is_cluster = is_cluster
                result.append(s)
        return result

    async def close(self):
        if self.client:
            await self.client.aclose()
            self.client = None
