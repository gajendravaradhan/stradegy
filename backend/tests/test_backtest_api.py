from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from stradegy.db import OHLCV, async_session, init_db
from stradegy.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def seed_ohlcv(ticker: str, days: int = 800):
    await init_db()
    async with async_session() as session:
        base_date = date(2020, 1, 1)
        records = []
        price = 100.0
        for i in range(days):
            d = base_date + timedelta(days=i)
            price = price + (i % 7 - 3) * 0.5
            records.append({
                "ticker_symbol": ticker,
                "date": d,
                "open": round(price - 0.5, 4),
                "high": round(price + 1.0, 4),
                "low": round(price - 1.0, 4),
                "close": round(price, 4),
                "volume": 1_000_000 + i * 100,
                "adjusted_close": round(price, 4),
            })
        session.add_all([OHLCV(**r) for r in records])
        await session.commit()


@pytest.mark.anyio
async def test_backtest_strategies_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/backtest/strategies")
    assert response.status_code == 200
    data = response.json()
    assert "strategies" in data
    assert len(data["strategies"]) == 4
    keys = [s["key"] for s in data["strategies"]]
    assert "ensemble" in keys
    assert "mean_reversion" in keys


@pytest.mark.anyio
async def test_backtest_run_with_data():
    await seed_ohlcv("TEST", days=800)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/backtest/run",
            params={
                "ticker": "TEST",
                "strategy": "mean_reversion",
                "train_size": 252,
                "test_size": 63,
                "step_size": 63,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "TEST"
    assert data["strategy"] == "mean_reversion"
    assert "windows_tested" in data
    assert "aggregate" in data
    assert "window_results" in data


@pytest.mark.anyio
async def test_backtest_run_insufficient_data():
    await seed_ohlcv("SHORT", days=50)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/backtest/run",
            params={
                "ticker": "SHORT",
                "strategy": "ensemble",
                "train_size": 200,
                "test_size": 100,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "Insufficient data" in data["error"]
