from datetime import date, datetime
from typing import Any

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from stradegy.db import DownloadLog, OHLCV, Ticker, get_newest_ohlcv_date


class DataStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_ohlcv_batch(self, records: list[dict]) -> int:
        if not records:
            return 0

        stmt = sqlite_insert(OHLCV).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["ticker_symbol", "date"]
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        inserted = result.rowcount if result.rowcount else 0
        logger.info(f"Upserted {inserted} OHLCV rows")
        return inserted

    async def get_ticker_data(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
    ) -> list[OHLCV]:
        stmt = select(OHLCV).where(OHLCV.ticker_symbol == symbol.upper())

        if start_date:
            stmt = stmt.where(OHLCV.date >= start_date)
        if end_date:
            stmt = stmt.where(OHLCV.date <= end_date)

        stmt = stmt.order_by(OHLCV.date.asc())

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_date(self, symbol: str) -> date | None:
        return await get_newest_ohlcv_date(self.session, symbol)

    async def get_data_range(
        self, symbol: str
    ) -> tuple[date | None, date | None]:
        from stradegy.db import get_oldest_ohlcv_date

        oldest = await get_oldest_ohlcv_date(self.session, symbol)
        newest = await get_newest_ohlcv_date(self.session, symbol)
        return oldest, newest

    async def save_ticker(self, symbol: str, **kwargs) -> Ticker:
        ticker = Ticker(symbol=symbol.upper(), **kwargs)
        self.session.add(ticker)
        await self.session.commit()
        await self.session.refresh(ticker)
        return ticker

    async def get_ticker(self, symbol: str) -> Ticker | None:
        result = await self.session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        return result.scalar_one_or_none()

    async def get_active_tickers(self) -> list[Ticker]:
        result = await self.session.execute(
            select(Ticker).where(Ticker.is_active == True)
        )
        return result.scalars().all()

    async def log_download_start(
        self, symbol: str, from_date: date | None, to_date: date | None
    ) -> DownloadLog:
        log = DownloadLog(
            ticker_symbol=symbol.upper(),
            status="running",
            from_date=from_date,
            to_date=to_date,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def log_download_complete(
        self, log_id: int, rows_fetched: int
    ):
        result = await self.session.execute(
            select(DownloadLog).where(DownloadLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if log:
            log.status = "completed"
            log.completed_at = datetime.utcnow()
            log.rows_fetched = rows_fetched
            await self.session.commit()

    async def log_download_error(self, log_id: int, error: str):
        result = await self.session.execute(
            select(DownloadLog).where(DownloadLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if log:
            log.status = "failed"
            log.completed_at = datetime.utcnow()
            log.error_message = error[:500]
            await self.session.commit()

    async def delete_ohlcv_for_ticker(self, symbol: str) -> int:
        result = await self.session.execute(
            delete(OHLCV).where(OHLCV.ticker_symbol == symbol.upper())
        )
        await self.session.commit()
        return result.rowcount or 0

    async def save_portfolio_snapshot(self, snapshot: dict) -> int:
        from stradegy.db import PortfolioSnapshot
        record = PortfolioSnapshot(**snapshot)
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record.id

    async def get_portfolio_history(self, days: int = 90) -> list[dict]:
        from datetime import date, timedelta
        from stradegy.db import PortfolioSnapshot
        start = date.today() - timedelta(days=days)
        result = await self.session.execute(
            select(PortfolioSnapshot).where(PortfolioSnapshot.date >= start).order_by(PortfolioSnapshot.date.asc())
        )
        records = result.scalars().all()
        return [
            {
                "date": r.date.isoformat(),
                "equity": float(r.equity),
                "buying_power": float(r.buying_power),
                "day_pnl": float(r.day_pnl),
                "open_positions": r.open_positions,
                "realized_gains": float(r.realized_gains),
                "tax_reserve": float(r.tax_reserve),
                "peak_equity": float(r.peak_equity) if r.peak_equity else None,
                "drawdown": float(r.drawdown),
            }
            for r in records
        ]

    async def get_ohlcv_dataframe(self, symbol: str, limit: int | None = None) -> Any:
        import pandas as pd

        records = await self.get_ticker_data(symbol, limit=limit)
        if not records:
            return None
        data = {
            "open": [float(r.open) for r in records],
            "high": [float(r.high) for r in records],
            "low": [float(r.low) for r in records],
            "close": [float(r.close) for r in records],
            "volume": [r.volume for r in records],
        }
        df = pd.DataFrame(data, index=[r.date for r in records])
        df.index = pd.to_datetime(df.index)
        return df

    async def get_latest_price(self, symbol: str) -> float | None:
        records = await self.get_ticker_data(symbol, limit=1)
        if not records:
            return None
        return float(records[0].close)
