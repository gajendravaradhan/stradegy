from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from stradegy.db import (
    OHLCV,
    Ticker,
    async_session,
    get_newest_ohlcv_date,
    get_oldest_ohlcv_date,
)
from stradegy.engine.data.store import DataStore
from stradegy.engine.data.ticker_universe import TickerUniverse
from stradegy.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def store(db_session):
    return DataStore(db_session)


@pytest.fixture
async def clean_db(db_session):
    from stradegy.db import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return db_session


class TestTickerUniverse:
    def test_default_universe_has_tickers(self):
        universe = TickerUniverse()
        tickers = universe.get_default_universe()
        assert len(tickers) > 50
        assert "AAPL" in tickers
        assert "MSFT" in tickers

    def test_load_custom_tickers_empty(self, tmp_path):
        universe = TickerUniverse(data_dir=tmp_path)
        assert universe.load_custom_tickers() == []

    def test_add_and_remove_custom_ticker(self, tmp_path):
        universe = TickerUniverse(data_dir=tmp_path)
        universe.add_custom_ticker("CUSTOM1")
        assert "CUSTOM1" in universe.load_custom_tickers()
        universe.remove_custom_ticker("CUSTOM1")
        assert "CUSTOM1" not in universe.load_custom_tickers()

    def test_full_universe_includes_custom(self, tmp_path):
        universe = TickerUniverse(data_dir=tmp_path)
        universe.add_custom_ticker("MYTICKER")
        full = universe.get_full_universe()
        assert "MYTICKER" in full
        assert "AAPL" in full


class TestDataStore:
    @pytest.mark.anyio
    async def test_save_and_get_ohlcv(self, clean_db, store):
        records = [
            {
                "ticker_symbol": "AAPL",
                "date": date(2024, 1, 1),
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000,
                "adjusted_close": 153.0,
            }
        ]
        inserted = await store.save_ohlcv_batch(records)
        assert inserted == 1

        data = await store.get_ticker_data("AAPL")
        assert len(data) == 1
        assert data[0].ticker_symbol == "AAPL"
        assert float(data[0].close) == 153.0

    @pytest.mark.anyio
    async def test_ohlcv_upsert_no_duplicate(self, clean_db, store):
        records = [
            {
                "ticker_symbol": "AAPL",
                "date": date(2024, 1, 1),
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000,
                "adjusted_close": 153.0,
            }
        ]
        await store.save_ohlcv_batch(records)
        inserted = await store.save_ohlcv_batch(records)
        assert inserted == 0

    @pytest.mark.anyio
    async def test_save_ticker(self, clean_db, store):
        ticker = await store.save_ticker(
            symbol="TEST",
            name="Test Corp",
            sector="Technology",
            is_active=True,
        )
        assert ticker.symbol == "TEST"

        fetched = await store.get_ticker("TEST")
        assert fetched is not None
        assert fetched.name == "Test Corp"

    @pytest.mark.anyio
    async def test_get_active_tickers(self, clean_db, store):
        await store.save_ticker(symbol="ACTIVE1", is_active=True)
        await store.save_ticker(symbol="INACTIVE1", is_active=False)

        active = await store.get_active_tickers()
        symbols = [t.symbol for t in active]
        assert "ACTIVE1" in symbols
        assert "INACTIVE1" not in symbols

    @pytest.mark.anyio
    async def test_data_range(self, clean_db, store):
        records = [
            {
                "ticker_symbol": "AAPL",
                "date": date(2020, 1, 1),
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 103.0,
                "volume": 1000000,
            },
            {
                "ticker_symbol": "AAPL",
                "date": date(2024, 1, 1),
                "open": 150.0,
                "high": 155.0,
                "low": 149.0,
                "close": 153.0,
                "volume": 1000000,
            },
        ]
        await store.save_ohlcv_batch(records)

        oldest, newest = await store.get_data_range("AAPL")
        assert oldest.isoformat() == "2020-01-01"
        assert newest.isoformat() == "2024-01-01"


class TestDataEndpoints:
    @pytest.mark.anyio
    async def test_seed_tickers_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/data/tickers/seed")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tickers_seeded"] > 0

    @pytest.mark.anyio
    async def test_list_tickers_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data/tickers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "symbol" in data[0]
            assert "is_active" in data[0]

    @pytest.mark.anyio
    async def test_data_range_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/data/tickers/AAPL/range")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "oldest_date" in data
        assert "newest_date" in data
