import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stradegy.db import async_session, init_db
from stradegy.engine.data.fetcher import DataFetcher
from stradegy.engine.data.store import DataStore


async def test_incremental():
    await init_db()

    async with async_session() as session:
        store = DataStore(session)
        fetcher = DataFetcher()

        latest = await store.get_latest_date("AAPL")
        print(f"Latest AAPL data: {latest}")

        yesterday = date.today() - __import__("datetime").timedelta(days=1)
        if latest and latest >= yesterday:
            print("AAPL is up to date, no incremental fetch needed")
        else:
            print("Fetching incremental data...")
            records = await fetcher.fetch_incremental("AAPL", latest)
            if records:
                inserted = await store.save_ohlcv_batch(records)
                print(f"Inserted {inserted} new rows")
            else:
                print("No new data to fetch")


if __name__ == "__main__":
    asyncio.run(test_incremental())
