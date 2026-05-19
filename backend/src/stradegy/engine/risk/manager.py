from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger

from stradegy.config import settings
from stradegy.engine.risk.tiers import get_tier_config


class RiskManager:
    def __init__(self):
        self.max_drawdown_limit = settings.max_drawdown
        self.stop_atr_mult = settings.stop_atr_mult

    def _tier_config(self, equity: float) -> dict[str, Any]:
        return get_tier_config(equity)

    def calculate_position_size(
        self,
        equity: float,
        atr: float,
        price: float,
    ) -> dict[str, Any]:
        if atr <= 0 or price <= 0:
            return {"shares": 0, "position_value": 0, "stop_loss": 0, "stop_distance": 0, "risk_amount": 0, "risk_pct": 0}

        tier = self._tier_config(equity)
        risk_per_trade = tier["risk_per_trade"]
        risk_amount = equity * risk_per_trade
        stop_distance = atr * self.stop_atr_mult
        shares = int(risk_amount / stop_distance)
        position_value = shares * price

        max_position_value = equity * 0.25
        if position_value > max_position_value:
            shares = int(max_position_value / price)
            position_value = shares * price

        stop_loss = price - stop_distance if shares > 0 else 0

        return {
            "shares": shares,
            "position_value": round(position_value, 2),
            "stop_loss": round(stop_loss, 2),
            "stop_distance": round(stop_distance, 2),
            "risk_amount": round(risk_amount, 2),
            "risk_pct": round((shares * stop_distance) / equity * 100, 2) if equity > 0 else 0,
            "tier": tier["tier"],
        }

    def check_drawdown(self, equity: float, peak_equity: float) -> dict[str, Any]:
        if peak_equity <= 0:
            return {"is_safe": True, "drawdown": 0.0}

        drawdown = (peak_equity - equity) / peak_equity
        is_safe = drawdown < self.max_drawdown_limit

        return {
            "is_safe": is_safe,
            "drawdown": round(drawdown, 4),
            "limit": self.max_drawdown_limit,
            "peak_equity": round(peak_equity, 2),
            "current_equity": round(equity, 2),
            "kill_switch": not is_safe,
        }

    def check_pdt(self, trades_last_5_days: list[date]) -> dict[str, Any]:
        cutoff = date.today() - timedelta(days=5)
        recent_day_trades = [t for t in trades_last_5_days if t > cutoff]
        count = len(recent_day_trades)
        limit = 3
        remaining = max(0, limit - count)

        return {
            "pdt_count": count,
            "pdt_limit": limit,
            "pdt_remaining": remaining,
            "pdt_violation": count >= limit,
            "can_trade": count < limit,
        }

    def calculate_tax_reserve(self, realized_gains: float) -> dict[str, Any]:
        tax_owed = realized_gains * settings.tax_rate_short_term
        reserve = tax_owed

        return {
            "realized_gains": round(realized_gains, 2),
            "tax_rate": settings.tax_rate_short_term,
            "tax_owed": round(tax_owed, 2),
            "reserve_required": round(reserve, 2),
            "message": f"Set aside ${reserve:,.2f} for taxes ({settings.tax_rate_short_term * 100:.0f}% of gains)",
        }

    def check_correlation(self, correlation_matrix: dict[str, dict[str, float]], threshold: float = 0.8) -> list[str]:
        high_corr = []
        tickers = list(correlation_matrix.keys())

        for i, t1 in enumerate(tickers):
            for t2 in tickers[i + 1:]:
                corr = correlation_matrix.get(t1, {}).get(t2, 0)
                if abs(corr) > threshold:
                    high_corr.append(f"{t1}-{t2}: {corr:.2f}")

        return high_corr

    def emergency_check(self, equity: float, peak_equity: float, pdt_data: dict, correlation_warnings: list) -> dict[str, Any]:
        dd_check = self.check_drawdown(equity, peak_equity)

        emergencies = []
        if dd_check["kill_switch"]:
            emergencies.append(f"DRAWDOWN: {dd_check['drawdown']:.1%} exceeds limit")
        if pdt_data.get("pdt_violation"):
            emergencies.append("PDT: Day trade limit reached")

        return {
            "is_emergency": len(emergencies) > 0,
            "emergencies": emergencies,
            "should_halt_trading": dd_check["kill_switch"] or pdt_data.get("pdt_violation", False),
            "drawdown_status": dd_check,
            "pdt_status": pdt_data,
            "correlation_warnings": correlation_warnings,
        }
