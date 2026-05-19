import pytest
from httpx import ASGITransport, AsyncClient

from stradegy.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"


@pytest.mark.anyio
async def test_account_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/account/summary")
    assert response.status_code == 200
    data = response.json()
    assert "equity" in data
    assert "buying_power" in data
    assert "mode" in data
    assert data["mode"] in ("paper", "live")
    assert data["autonomy"] in ("semi", "full")


@pytest.mark.anyio
async def test_cors_headers_present():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


@pytest.mark.anyio
async def test_list_backtest_strategies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/backtest/strategies")
    assert response.status_code == 200
    data = response.json()
    assert "strategies" in data
    assert len(data["strategies"]) == 4



