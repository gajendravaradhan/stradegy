from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from stradegy.config import settings


class PerformanceMetrics:
    @staticmethod
    def calculate(trades: list[dict[str, Any]]) -> dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "total_pnl": 0.0,
                "expectancy": 0.0,
            }

        pnls = [t.get("pnl", 0) or 0 for t in trades if t.get("action") == "exit"]
        if not pnls:
            pnls = [t.get("pnl", 0) or 0 for t in trades]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_trades = len(pnls)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0

        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float("inf")

        avg_win = (total_wins / len(wins)) if wins else 0.0
        avg_loss = (total_losses / len(losses)) if losses else 0.0
        total_pnl = sum(pnls)

        expectancy = ((win_rate / 100) * avg_win) - ((1 - win_rate / 100) * avg_loss) if total_trades > 0 else 0.0

        sharpe = PerformanceMetrics._sharpe_ratio(pnls)
        max_dd = PerformanceMetrics._max_drawdown(pnls)

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 4),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_pnl": round(total_pnl, 2),
            "expectancy": round(expectancy, 2),
        }

    @staticmethod
    def _sharpe_ratio(pnls: list[float], risk_free_rate: float = 0.0) -> float:
        if not pnls or len(pnls) < 2:
            return 0.0
        returns = np.array(pnls)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        if std_return == 0:
            return 0.0
        return (mean_return - risk_free_rate) / std_return

    @staticmethod
    def _max_drawdown(pnls: list[float]) -> float:
        if not pnls:
            return 0.0
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / np.maximum(peak, 1e-9)
        return float(np.min(drawdown))


def get_performance_metrics(days: int = 90) -> dict[str, Any]:
    from stradegy.engine.self_improvement.tracer import TradeTracer
    tracer = TradeTracer()
    start = date.today() - __import__("datetime").timedelta(days=days)
    trades = tracer.get_by_date_range(start, date.today())
    metrics = PerformanceMetrics.calculate(trades)
    metrics["period_days"] = days
    return metrics
