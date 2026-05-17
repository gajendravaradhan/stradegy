from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from stradegy.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass




class Ticker(Base):
    __tablename__ = "tickers"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=True)
    sector: Mapped[str] = mapped_column(String(128), nullable=True)
    industry: Mapped[str] = mapped_column(String(128), nullable=True)
    market_cap: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_watched: Mapped[bool] = mapped_column(default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    source: Mapped[str] = mapped_column(String(64), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class OHLCV(Base):
    __tablename__ = "ohlcv"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    adjusted_close: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker_symbol", "date", name="uix_ohlcv_ticker_date"),
    )


class DownloadLog(Base):
    __tablename__ = "download_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    from_date: Mapped[date] = mapped_column(Date, nullable=True)
    to_date: Mapped[date] = mapped_column(Date, nullable=True)
    rows_fetched: Mapped[int] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str] = mapped_column(String(512), nullable=True)


class MarketMetadata(Base):
    __tablename__ = "market_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    record_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=True)
    value: Mapped[str] = mapped_column(String(512), nullable=True)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    buying_power: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    day_pnl: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=Decimal("0"))
    open_positions: Mapped[int] = mapped_column(Integer, default=0)
    realized_gains: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=Decimal("0"))
    tax_reserve: Mapped[Decimal] = mapped_column(Numeric(16, 4), default=Decimal("0"))
    peak_equity: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=True)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("date", name="uix_snapshot_date"),
    )


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_oldest_ohlcv_date(
    session: AsyncSession, ticker_symbol: str
) -> date | None:
    result = await session.execute(
        select(func.min(OHLCV.date)).where(OHLCV.ticker_symbol == ticker_symbol)
    )
    return result.scalar_one_or_none()


async def get_newest_ohlcv_date(
    session: AsyncSession, ticker_symbol: str
) -> date | None:
    result = await session.execute(
        select(func.max(OHLCV.date)).where(OHLCV.ticker_symbol == ticker_symbol)
    )
    return result.scalar_one_or_none()


async def count_ohlcv_rows(
    session: AsyncSession, ticker_symbol: str
) -> int:
    result = await session.execute(
        select(func.count()).where(OHLCV.ticker_symbol == ticker_symbol)
    )
    return result.scalar_one_or_none() or 0
