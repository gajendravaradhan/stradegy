from datetime import datetime, timezone
from typing import Any

from loguru import logger

from stradegy.config import settings


class AlpacaClient:
    def __init__(self):
        self.api_key = settings.alpaca_api_key
        self.secret_key = settings.alpaca_secret_key
        self.base_url = settings.alpaca_base_url
        self.paper = settings.paper_trading
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                from alpaca.trading.client import TradingClient
                self._client = TradingClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key,
                    paper=self.paper,
                )
                logger.info(f"Alpaca client initialized ({'paper' if self.paper else 'LIVE'})")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca client: {e}")
                raise

    async def get_account(self) -> dict[str, Any]:
        self._ensure_client()
        try:
            account = self._client.get_account()
            return {
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "status": account.status,
            }
        except Exception as e:
            logger.error(f"Error fetching account: {e}")
            return {}

    async def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        limit_price: float | None = None,
    ) -> dict[str, Any]:
        self._ensure_client()
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce

            side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            if order_type == "market":
                order = MarketOrderRequest(
                    symbol=symbol.upper(),
                    qty=qty,
                    side=side_enum,
                    time_in_force=TimeInForce.DAY,
                )
            else:
                order = LimitOrderRequest(
                    symbol=symbol.upper(),
                    qty=qty,
                    side=side_enum,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price,
                )

            submitted = self._client.submit_order(order)
            return {
                "id": str(submitted.id),
                "symbol": submitted.symbol,
                "qty": float(submitted.qty) if submitted.qty else 0,
                "side": submitted.side.value,
                "status": submitted.status.value,
                "created_at": submitted.created_at,
            }
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            return {"error": str(e)}

    async def get_positions(self) -> list[dict[str, Any]]:
        self._ensure_client()
        try:
            positions = self._client.get_all_positions()
            return [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "avg_entry_price": float(p.avg_entry_price) if p.avg_entry_price else 0,
                    "market_value": float(p.market_value) if p.market_value else 0,
                    "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else 0,
                    "unrealized_plpc": float(p.unrealized_plpc) if p.unrealized_plpc else 0,
                }
                for p in positions
            ]
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def get_order(self, order_id: str) -> dict[str, Any]:
        self._ensure_client()
        try:
            order = self._client.get_order_by_id(order_id)
            return {
                "id": str(order.id),
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else 0,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "side": order.side.value if order.side else "unknown",
                "status": order.status.value if order.status else "unknown",
                "created_at": order.created_at,
                "updated_at": order.updated_at,
            }
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return {"error": str(e)}

    async def poll_order_fill(
        self, order_id: str, timeout: int = 30, interval: int = 2
    ) -> dict[str, Any]:
        import asyncio
        import time

        start = time.time()
        while time.time() - start < timeout:
            order = await self.get_order(order_id)
            if order.get("error"):
                logger.error(f"Order {order_id} error during poll: {order['error']}")
                return {**order, "poll_timeout": False}

            status = order.get("status", "").lower()
            if status in ("filled", "partially_filled"):
                logger.info(
                    f"Order {order_id} {status}: filled {order.get('filled_qty', 0)}/{order.get('qty', 0)}"
                )
                return {**order, "poll_timeout": False}
            if status in ("canceled", "expired", "rejected", "stopped"):
                logger.warning(f"Order {order_id} terminal status: {status}")
                return {**order, "poll_timeout": False}

            await asyncio.sleep(interval)

        logger.warning(f"Order {order_id} polling timed out after {timeout}s")
        return {**order, "poll_timeout": True}

    async def close_position(self, symbol: str) -> dict[str, Any]:
        self._ensure_client()
        try:
            result = self._client.close_position(symbol.upper())
            return {
                "symbol": result.symbol,
                "qty": float(result.qty) if result.qty else 0,
                "status": result.status.value if result.status else "unknown",
            }
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"error": str(e)}
