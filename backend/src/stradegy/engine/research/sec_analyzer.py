from datetime import datetime, timezone
from typing import Any

from edgar import Company, set_identity
from loguru import logger

from stradegy.config import settings
from stradegy.engine.research.models import SECFiling


class SECAnalyzer:
    def __init__(self):
        self._identity_set = False

    def _ensure_identity(self):
        if not self._identity_set:
            set_identity("Stradegy contact@stradegy.dev")
            self._identity_set = True

    def get_latest_filing(
        self, ticker: str, form_type: str = "10-K"
    ) -> dict[str, Any] | None:
        self._ensure_identity()
        try:
            company = Company(ticker)
            filing = company.latest(form_type)
            if not filing:
                logger.warning(f"No {form_type} found for {ticker}")
                return None
            return {
                "ticker": ticker.upper(),
                "form_type": form_type,
                "filing_date": filing.filing_date,
                "url": filing.filing_url,
            }
        except Exception as e:
            logger.error(f"Error fetching {form_type} for {ticker}: {e}")
            return None

    def analyze_10k(self, ticker: str) -> SECFiling | None:
        self._ensure_identity()
        try:
            company = Company(ticker)
            filing = company.latest("10-K")
            if not filing:
                return None

            xbrl = filing.xbrl()
            statements = xbrl.statements if xbrl else None

            revenue = self._extract_revenue(statements)
            gross_margin = self._extract_gross_margin(statements)
            operating_margin = self._extract_operating_margin(statements)
            cash = self._extract_cash(statements)
            debt = self._extract_debt(statements)
            cash_ratio = cash / debt if debt and debt > 0 else (999 if cash else None)

            return SECFiling(
                ticker_symbol=ticker,
                filing_type="10-K",
                filing_date=filing.filing_date,
                filing_url=filing.filing_url,
                revenue_growth_yoy=revenue.get("growth") if revenue else None,
                gross_margin=gross_margin,
                operating_margin=operating_margin,
                cash_to_debt_ratio=cash_ratio,
            )
        except Exception as e:
            logger.error(f"Error analyzing 10-K for {ticker}: {e}")
            return None

    def analyze_insider_activity(self, ticker: str) -> int:
        self._ensure_identity()
        try:
            company = Company(ticker)
            forms4 = company.get_filings(form="4")
            net_buys = 0
            for f in forms4[:10]:
                net_buys += 1
            return net_buys
        except Exception as e:
            logger.error(f"Error analyzing insider activity for {ticker}: {e}")
            return 0

    def _extract_revenue(self, statements) -> dict[str, Any] | None:
        try:
            income = statements.income_statement() if statements else None
            if income:
                rev = income.get("Revenue", income.get("Total Revenue"))
                return {"value": rev, "growth": None}
        except Exception:
            pass
        return None

    def _extract_gross_margin(self, statements) -> float | None:
        try:
            income = statements.income_statement() if statements else None
            if income:
                revenue = income.get("Revenue", income.get("Total Revenue"))
                cogs = income.get("Cost of Revenue", income.get("Cost of Goods Sold"))
                if revenue and cogs and revenue > 0:
                    return round((revenue - cogs) / revenue, 4)
        except Exception:
            pass
        return None

    def _extract_operating_margin(self, statements) -> float | None:
        try:
            income = statements.income_statement() if statements else None
            if income:
                revenue = income.get("Revenue", income.get("Total Revenue"))
                op_income = income.get("Operating Income")
                if revenue and op_income and revenue > 0:
                    return round(op_income / revenue, 4)
        except Exception:
            pass
        return None

    def _extract_cash(self, statements) -> float | None:
        try:
            bs = statements.balance_sheet() if statements else None
            if bs:
                return bs.get("Cash and Cash Equivalents")
        except Exception:
            pass
        return None

    def _extract_debt(self, statements) -> float | None:
        try:
            bs = statements.balance_sheet() if statements else None
            if bs:
                return bs.get("Total Debt", bs.get("Long Term Debt"))
        except Exception:
            pass
        return None
