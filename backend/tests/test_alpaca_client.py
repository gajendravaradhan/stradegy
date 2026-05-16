import pytest
from unittest.mock import MagicMock, patch

from stradegy.engine.execution.alpaca_client import AlpacaClient


@pytest.fixture
def client():
    with patch.dict("os.environ", {"ALPACA_API_KEY": "test_key", "ALPACA_SECRET_KEY": "test_secret"}, clear=False):
        c = AlpacaClient()
        c.api_key = "test_key"
        c.secret_key = "test_secret"
        c.paper = True
        return c


@pytest.fixture
def mock_account():
    acc = MagicMock()
    acc.equity = "25000.00"
    acc.buying_power = "50000.00"
    acc.cash = "25000.00"
    acc.portfolio_value = "25000.00"
    acc.status = "ACTIVE"
    return acc


@pytest.fixture
def mock_order():
    order = MagicMock()
    order.id = "order-id-123"
    order.symbol = "AAPL"
    order.qty = "10"
    order.side = MagicMock()
    order.side.value = "buy"
    order.status = MagicMock()
    order.status.value = "filled"
    order.created_at = "2025-01-01T00:00:00Z"
    return order


@pytest.fixture
def mock_position():
    pos = MagicMock()
    pos.symbol = "AAPL"
    pos.qty = "10"
    pos.avg_entry_price = "150.00"
    pos.market_value = "1600.00"
    pos.unrealized_pl = "100.00"
    pos.unrealized_plpc = "0.0667"
    return pos


@pytest.mark.anyio
async def test_get_account(client, mock_account):
    client._client = MagicMock()
    client._client.get_account.return_value = mock_account

    result = await client.get_account()
    assert result["equity"] == 25000.0
    assert result["buying_power"] == 50000.0
    assert result["cash"] == 25000.0
    assert result["status"] == "ACTIVE"


@pytest.mark.anyio
async def test_get_account_error(client):
    client._client = MagicMock()
    client._client.get_account.side_effect = Exception("network error")

    result = await client.get_account()
    assert result == {}


@pytest.mark.anyio
async def test_submit_market_order(client, mock_order):
    client._client = MagicMock()
    client._client.submit_order.return_value = mock_order

    result = await client.submit_order("aapl", 10, "buy", "market")
    assert result["symbol"] == "AAPL"
    assert result["qty"] == 10.0
    assert result["side"] == "buy"
    assert result["status"] == "filled"
    assert "id" in result


@pytest.mark.anyio
async def test_submit_limit_order(client, mock_order):
    limit_mock = MagicMock()
    limit_mock.id = "order-id-456"
    limit_mock.symbol = "AAPL"
    limit_mock.qty = "5"
    limit_mock.side = MagicMock()
    limit_mock.side.value = "sell"
    limit_mock.status = MagicMock()
    limit_mock.status.value = "new"
    limit_mock.created_at = "2025-01-01T00:00:00Z"

    client._client = MagicMock()
    client._client.submit_order.return_value = limit_mock

    result = await client.submit_order("aapl", 5, "sell", "limit", limit_price=150.0)
    assert result["symbol"] == "AAPL"
    assert result["qty"] == 5.0
    assert result["side"] == "sell"


@pytest.mark.anyio
async def test_submit_order_error(client):
    client._client = MagicMock()
    client._client.submit_order.side_effect = Exception("rejected")

    result = await client.submit_order("aapl", 10, "buy")
    assert "error" in result


@pytest.mark.anyio
async def test_get_positions(client, mock_position):
    client._client = MagicMock()
    client._client.get_all_positions.return_value = [mock_position]

    result = await client.get_positions()
    assert len(result) == 1
    assert result[0]["symbol"] == "AAPL"
    assert result[0]["qty"] == 10.0
    assert result[0]["avg_entry_price"] == 150.0


@pytest.mark.anyio
async def test_get_positions_error(client):
    client._client = MagicMock()
    client._client.get_all_positions.side_effect = Exception("error")

    result = await client.get_positions()
    assert result == []


@pytest.mark.anyio
async def test_close_position(client):
    mock_closed = MagicMock()
    mock_closed.symbol = "AAPL"
    mock_closed.qty = "10"
    mock_closed.status = MagicMock()
    mock_closed.status.value = "closed"

    client._client = MagicMock()
    client._client.close_position.return_value = mock_closed

    result = await client.close_position("aapl")
    assert result["symbol"] == "AAPL"
    assert result["qty"] == 10.0
    assert result["status"] == "closed"


@pytest.mark.anyio
async def test_close_position_error(client):
    client._client = MagicMock()
    client._client.close_position.side_effect = Exception("no position")

    result = await client.close_position("aapl")
    assert "error" in result


def test_ensure_client_initializes():
    with patch("alpaca.trading.client.TradingClient") as MockTradingClient:
        client = AlpacaClient()
        client.api_key = "k"
        client.secret_key = "s"
        client.paper = True
        client._ensure_client()
        assert client._client is not None
        MockTradingClient.assert_called_once_with(api_key="k", secret_key="s", paper=True)
