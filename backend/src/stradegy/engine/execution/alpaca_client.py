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
