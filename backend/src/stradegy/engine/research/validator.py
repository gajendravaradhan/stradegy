import re
from datetime import date, timedelta
from typing import Any

from loguru import logger

from stradegy.engine.research.models import GemSignal, ValidationResult


class Validator:
    PUMP_DUMP_PATTERNS = [
        r"\bto\s+the\s+moon\b",
        r"\bguaranteed\s+\d+x\b",
        r"\b100x\s+gem\b",
        r"\bnext\s+(?:bitcoin|eth|tesla)\b",
        r"\bbuy\s+now\s+or\s+regret\b",
        r"\bwall\s+street\s+bets\s+pump\b",
        r"\bmoon\s+shot\b",
        r"\brocket\s+emoji\b",
        r"\b1000x\b",
        r"\b10x\s+guaranteed\b",
    ]

    PRICE_MOVEMENT_THRESHOLD = 0.15
    MIN_MARKET_CAP = 10_000_000
    MAX_MARKET_CAP = 2_000_000_000

    def __init__(self, store=None):
        self.store = store

    async def validate(self, gem: GemSignal, current_price: float | None = None) -> ValidationResult:
        checks = {}
        failures = []

        active = await self._check_active_trading(gem.ticker_symbol)
        checks["active_trading"] = active
        if not active:
            failures.append("Ticker not actively trading or no recent data")

        pump_dump = self._check_pump_dump(gem)
        checks["pump_dump"] = not pump_dump
        if pump_dump:
            failures.append("Pump-and-dump language detected")

        price_ok = await self._check_price_movement(gem.ticker_symbol, current_price)
        checks["price_movement"] = price_ok
        if not price_ok:
            failures.append("Price already moved > 15% since signal")

        market_cap_ok = await self._check_market_cap(gem.ticker_symbol)
        checks["market_cap"] = market_cap_ok
        if not market_cap_ok:
            failures.append("Market cap outside $10M-$2B range")

        cross_ref = gem.source_count >= 2
        checks["cross_reference"] = cross_ref
        if not cross_ref:
            failures.append("Less than 2 independent signal sources")

        evidence_ok = len(gem.evidence_urls) > 0
        checks["evidence"] = evidence_ok
        if not evidence_ok:
            failures.append("No evidence URLs provided")

        is_valid = all(checks.values())

        return ValidationResult(
            ticker_symbol=gem.ticker_symbol,
            is_valid=is_valid,
            checks=checks,
            failures=failures,
            source_count=gem.source_count,
        )

    async def _check_active_trading(self, ticker: str) -> bool:
        if not self.store:
            return True
        try:
            latest = await self.store.get_latest_date(ticker)
            if not latest:
                return False
            return (date.today() - latest).days <= 7
        except Exception as e:
            logger.warning(f"Active trading check failed for {ticker}: {e}")
            return True

    def _check_pump_dump(self, gem: GemSignal) -> bool:
        text = " ".join(gem.evidence_urls)
        for source in gem.sources:
            if hasattr(source, "summary") and source.summary:
                text += " " + source.summary
        text = text.lower()
        for pattern in self.PUMP_DUMP_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Pump-dump pattern matched for {gem.ticker_symbol}: {pattern}")
                return True
        return False

    async def _check_price_movement(self, ticker: str, current_price: float | None) -> bool:
        if not self.store:
            return True
        try:
            end = date.today()
            start = end - timedelta(days=14)
            records = await self.store.get_ticker_data(ticker, start_date=start, end_date=end)
            if not records or len(records) < 2:
                return True
            prices = [float(r.close) for r in records]
            if prices[0] <= 0:
                return True
            pct_change = abs(prices[-1] - prices[0]) / prices[0]
            return pct_change <= self.PRICE_MOVEMENT_THRESHOLD
        except Exception as e:
            logger.warning(f"Price movement check failed for {ticker}: {e}")
            return True

    async def _check_market_cap(self, ticker: str) -> bool:
        if not self.store:
            return True
        try:
            ticker_obj = await self.store.get_ticker(ticker)
            if ticker_obj and hasattr(ticker_obj, "market_cap") and ticker_obj.market_cap:
                cap = ticker_obj.market_cap
                return self.MIN_MARKET_CAP <= cap <= self.MAX_MARKET_CAP
            import yfinance as yf
            info = yf.Ticker(ticker).info
            cap = info.get("marketCap") or info.get("market_cap")
            if cap:
                return self.MIN_MARKET_CAP <= cap <= self.MAX_MARKET_CAP
            return True
        except Exception as e:
            logger.warning(f"Market cap check failed for {ticker}: {e}")
            return True
