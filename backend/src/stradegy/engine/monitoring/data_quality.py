from datetime import date, datetime, timedelta, timezone
from typing import Any

from loguru import logger

from stradegy.db import async_session
from stradegy.engine.data.store import DataStore


class DataQualityAuditor:
    def __init__(self):
        self.gap_threshold_days = 5

    async def run_audit(self) -> dict[str, Any]:
        issues = []
        async with async_session() as session:
            store = DataStore(session)
            tickers = await store.get_active_tickers()
            yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
            for ticker in tickers:
                try:
                    latest = await store.get_latest_date(ticker.symbol)
                    if not latest:
                        issues.append({
                            "type": "missing_data",
                            "ticker": ticker.symbol,
                            "message": "No OHLCV data found",
                        })
                        continue
                    gap_days = (yesterday - latest).days
                    if gap_days > self.gap_threshold_days:
                        issues.append({
                            "type": "stale_data",
                            "ticker": ticker.symbol,
                            "message": f"Data {gap_days} days stale (last: {latest})",
                        })
                    df = await store.get_ohlcv_dataframe(ticker.symbol, limit=30)
                    if df is not None and len(df) > 1:
                        for i in range(1, len(df)):
                            expected = df.iloc[i - 1]["date"] + timedelta(days=1)
                            actual = df.iloc[i]["date"]
                            if expected != actual and expected.weekday() < 5 and actual.weekday() < 5:
                                issues.append({
                                    "type": "missing_bars",
                                    "ticker": ticker.symbol,
                                    "message": f"Missing bar {expected}",
                                })
                except Exception as e:
                    logger.warning(f"Audit error for {ticker.symbol}: {e}")

        summary = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "tickers_checked": len(tickers),
            "issues_found": len(issues),
            "issues": issues[:20],
        }
        if issues:
            logger.warning(f"Data quality audit: {len(issues)} issues across {len(tickers)} tickers")
        else:
            logger.info(f"Data quality audit: clean across {len(tickers)} tickers")
        return summary
