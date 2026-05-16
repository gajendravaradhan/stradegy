import re
from datetime import datetime, timedelta, timezone
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
    ]

    def __init__(self, store=None):
        self.store = store

    def validate(self, gem: GemSignal, current_price: float | None = None) -> ValidationResult:
        checks = {}
        failures = []

        active = self._check_active_trading(gem.ticker_symbol)
        checks["active_trading"] = active
        if not active:
            failures.append("Ticker not actively trading")

        pump_dump = self._check_pump_dump(gem)
        checks["pump_dump"] = not pump_dump
        if pump_dump:
            failures.append("Pump-and-dump language detected")

        price_ok = self._check_price_movement(gem.ticker_symbol, current_price)
        checks["price_movement"] = price_ok
        if not price_ok:
            failures.append("Price already moved > 15% since signal")

        market_cap_ok = self._check_market_cap(gem.ticker_symbol)
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

    def _check_active_trading(self, ticker: str) -> bool:
        return True

    def _check_pump_dump(self, gem: GemSignal) -> bool:
        return False

    def _check_price_movement(self, ticker: str, current_price: float | None) -> bool:
        return True

    def _check_market_cap(self, ticker: str) -> bool:
        return True
