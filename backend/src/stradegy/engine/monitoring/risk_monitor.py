from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from loguru import logger

from stradegy.config import settings
from stradegy.db import async_session
from stradegy.engine.data.store import DataStore
from stradegy.engine.execution.alpaca_client import AlpacaClient


class RiskMonitor:
    def __init__(self):
        self.max_drawdown = settings.max_drawdown
        self.paper = settings.paper_trading
        self.alert_cooldowns: dict[str, datetime] = {}

    async def _is_market_open(self) -> bool:
        now = datetime.now(timezone.utc)
        if now.weekday() >= 5:
            return False
        et = now.astimezone(__import__("zoneinfo").ZoneInfo("US/Eastern"))
        market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= et < market_close

    async def check_portfolio_risk(self) -> dict[str, Any]:
        if not await self._is_market_open():
            return {"status": "market_closed", "alerts": []}

        alerts = []
        drawdown = 0.0
        equity = 0.0
        try:
            client = AlpacaClient()
            try:
                account = await client.get_account()
                if not account:
                    return {"status": "error", "alerts": alerts}

                equity = float(account.get("equity", 0))
                positions = await client.get_positions()

                async with async_session() as session:
                    store = DataStore(session)
                    history = await store.get_portfolio_history(days=90)
                    peak_equity = equity
                    for h in history:
                        if h.get("peak_equity") and h["peak_equity"] > peak_equity:
                            peak_equity = h["peak_equity"]
                        elif h.get("equity") and h["equity"] > peak_equity:
                            peak_equity = h["equity"]

                    if peak_equity > 0:
                        drawdown = (peak_equity - equity) / peak_equity
                        if drawdown >= self.max_drawdown:
                            alerts.append({
                                "type": "drawdown_kill_switch",
                                "severity": "critical",
                                "message": f"Drawdown {drawdown:.1%} exceeded limit {self.max_drawdown:.1%}. Trading halted.",
                                "equity": equity,
                                "peak": peak_equity,
                            })
                        elif drawdown >= self.max_drawdown * 0.75:
                            alerts.append({
                                "type": "drawdown_warning",
                                "severity": "warning",
                                "message": f"Drawdown at {drawdown:.1%} (limit: {self.max_drawdown:.1%})",
                            })

                    if positions and equity > 0:
                        for pos in positions:
                            market_value = float(pos.get("market_value", 0))
                            pct = market_value / equity
                            if pct >= 0.25:
                                alerts.append({
                                    "type": "concentration_warning",
                                    "severity": "warning",
                                    "message": f"{pos['symbol']} is {pct:.1%} of portfolio (max 25%)",
                                    "symbol": pos["symbol"],
                                    "pct": pct,
                                })

                    pdt_count = await self._count_day_trades(store)
                    if pdt_count >= 3:
                        alerts.append({
                            "type": "pdt_warning",
                            "severity": "warning",
                            "message": f"PDT limit reached: {pdt_count}/3 day trades in 5 days",
                        })
            finally:
                await client.close()

            return {"status": "ok", "equity": equity, "drawdown": drawdown, "alerts": alerts}
        except Exception as e:
            logger.error(f"Risk monitor error: {e}")
            return {"status": "error", "alerts": alerts}

    async def _count_day_trades(self, store: DataStore) -> int:
        try:
            five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
            trades = await store.get_trades(since=five_days_ago)
            day_trades = 0
            seen_days = set()
            for t in trades:
                if t.get("action") == "sell" and t.get("status") == "filled":
                    day = t.get("created_at", datetime.now()).date()
                    if day not in seen_days:
                        seen_days.add(day)
                        day_trades += 1
            return day_trades
        except Exception:
            return 0

    def should_alert(self, alert_type: str, cooldown_minutes: int = 30) -> bool:
        now = datetime.now(timezone.utc)
        last = self.alert_cooldowns.get(alert_type)
        if last and (now - last).total_seconds() < cooldown_minutes * 60:
            return False
        self.alert_cooldowns[alert_type] = now
        return True
