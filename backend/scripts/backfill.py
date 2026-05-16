import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stradegy.config import settings
from stradegy.db import init_db
from stradegy.engine.data.fetcher import DataFetcher
from stradegy.engine.data.store import DataStore
from stradegy.engine.data.ticker_universe import TickerUniverse
from sqlalchemy.ext.asyncio import AsyncSession
from stradegy.db import async_session


async def run_backfill(tickers: list[str] | None = None, batch_size: int = 50):
    print("Initializing database...")
    await init_db()
    print("Database ready.")

    universe = TickerUniverse()
    if not tickers:
        tickers = universe.get_active_universe()

    print(f"Backfilling {len(tickers)} tickers with 20+ years of data...")
    print(f"Batch size: {batch_size}")
    print("-" * 60)

    async with async_session() as session:
        store = DataStore(session)
        fetcher = DataFetcher(calls_per_second=1.5)

        total_inserted = 0
        total_tickers = len(tickers)

        for i in range(0, total_tickers, batch_size):
            batch = tickers[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_tickers - 1) // batch_size + 1

            print(f"\n[Batch {batch_num}/{total_batches}] Processing {len(batch)} tickers: {', '.join(batch[:5])}{'...' if len(batch) > 5 else ''}")

            results = await fetcher.fetch_tickers(batch, period="20y")

            batch_inserted = 0
            for symbol, records in results.items():
                if records:
                    inserted = await store.save_ohlcv_batch(records)
                    batch_inserted += inserted
                    print(f"  {symbol}: {len(records)} rows fetched, {inserted} inserted")
                else:
                    print(f"  {symbol}: No data returned")

            total_inserted += batch_inserted
            print(f"  Batch total: {batch_inserted} rows inserted")

            if i + batch_size < total_tickers:
                print("  Pausing 5s between batches...")
                await asyncio.sleep(5)

    print("-" * 60)
    print(f"Backfill complete!")
    print(f"Total tickers processed: {total_tickers}")
    print(f"Total rows inserted: {total_inserted}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backfill historical stock data")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to backfill")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size (default: 10)")
    args = parser.parse_args()

    asyncio.run(run_backfill(tickers=args.tickers, batch_size=args.batch_size))
