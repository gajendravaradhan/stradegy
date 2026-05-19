import asyncio
from datetime import date, datetime, timedelta
from typing import Any

import yfinance as yf
from loguru import logger

from stradegy.config import settings
from stradegy.db import DownloadLog


class RateLimiter:
    def __init__(self, calls_per_second: float = 2.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_call = asyncio.get_event_loop().time()


class DataFetcher:
    def __init__(
        self,
        max_retries: int = 3,
        calls_per_second: float = 2.0,
        chunk_size: int = 100,
    ):
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(calls_per_second)
        self.chunk_size = chunk_size

    async def fetch_ticker(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        period: str | None = None,
    ) -> list[dict[str, Any]]:
        if not start_date and not period:
            period = "20y"

        end_date = end_date or date.today()
        start_date = start_date or (end_date - timedelta(days=7300))

        await self.rate_limiter.acquire()

        for attempt in range(1, self.max_retries + 1):
            try:
                ticker = yf.Ticker(symbol)

                if period:
                    hist = ticker.history(period=period, auto_adjust=False)
                else:
                    hist = ticker.history(
                        start=start_date.strftime("%Y-%m-%d"),
                        end=end_date.strftime("%Y-%m-%d"),
                        auto_adjust=False,
                    )

                if hist.empty:
                    logger.warning(f"No data returned for {symbol}")
                    return []

                records = []
                for idx, row in hist.iterrows():
                    records.append(
                        {
                            "ticker_symbol": symbol.upper(),
                            "date": idx.date(),
                            "open": round(float(row["Open"]), 4),
                            "high": round(float(row["High"]), 4),
                            "low": round(float(row["Low"]), 4),
                            "close": round(float(row["Close"]), 4),
                            "volume": int(row["Volume"]),
                            "adjusted_close": (
                                round(float(row["Adj Close"]), 4)
                                if "Adj Close" in row and not row.isna()["Adj Close"]
                                else None
                            ),
                        }
                    )

                logger.info(
                    f"Fetched {len(records)} rows for {symbol} "
                    f"({records[0]['date']} to {records[-1]['date']})"
                )
                return records

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed for {symbol}: {e}"
                )
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"All retries exhausted for {symbol}")
                    raise

        return []

    async def fetch_tickers(
        self,
        symbols: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
        period: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        results = {}
        total = len(symbols)

        for i, symbol in enumerate(symbols, 1):
            try:
                records = await self.fetch_ticker(
                    symbol, start_date=start_date, end_date=end_date, period=period
                )
                results[symbol] = records
                logger.info(f"Progress: {i}/{total} tickers processed")
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = []

        return results

    async def fetch_incremental(
        self,
        symbol: str,
        existing_latest_date: date | None,
    ) -> list[dict[str, Any]]:
        if not existing_latest_date:
            return await self.fetch_ticker(symbol, period="20y")

        yesterday = date.today() - timedelta(days=1)
        if existing_latest_date >= yesterday:
            logger.info(f"{symbol} is up to date (last: {existing_latest_date})")
            return []

        return await self.fetch_ticker(
            symbol,
            start_date=existing_latest_date + timedelta(days=1),
            end_date=yesterday,
        )


async def run_full_backfill(
    symbols: list[str],
    store: Any,
    batch_size: int = 50,
) -> dict[str, int]:
    fetcher = DataFetcher()
    stats = {"success": 0, "failed": 0, "total_rows": 0}

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        logger.info(
            f"Processing batch {i // batch_size + 1}/"
            f"{(len(symbols) - 1) // batch_size + 1} ({len(batch)} tickers)"
        )

        results = await fetcher.fetch_tickers(batch)

        for symbol, records in results.items():
            if records:
                await store.save_ohlcv_batch(records)
                stats["success"] += 1
                stats["total_rows"] += len(records)
            else:
                stats["failed"] += 1

        if i + batch_size < len(symbols):
            logger.info("Pausing between batches...")
            await asyncio.sleep(5)

    logger.info(
        f"Backfill complete: {stats['success']} success, "
        f"{stats['failed']} failed, {stats['total_rows']} total rows"
    )
    return stats
