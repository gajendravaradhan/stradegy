from datetime import date
from typing import Any

import numpy as np
from loguru import logger

from stradegy.engine.self_improvement.tracer import TradeTracer


class TraceAnalyzer:
    def __init__(self, tracer: TradeTracer | None = None):
        self.tracer = tracer or TradeTracer()

    def analyze_by_strategy(self, days: int = 30) -> dict[str, dict[str, Any]]:
        cutoff = date.today() - __import__("datetime").timedelta(days=days)
        trades = self.tracer.get_by_date_range(cutoff, date.today())
        if not trades:
            return {}

        by_strategy: dict[str, list[dict[str, Any]]] = {}
        for t in trades:
            by_strategy.setdefault(t["strategy"], []).append(t)

        results = {}
        for strategy, records in by_strategy.items():
            pnls = [r["pnl"] for r in records if r.get("pnl") is not None]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]

            results[strategy] = {
                "total_trades": len(records),
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate": len(wins) / len(pnls) if pnls else 0.0,
                "avg_pnl": float(np.mean(pnls)) if pnls else 0.0,
                "total_pnl": sum(pnls) if pnls else 0.0,
                "avg_confidence": float(np.mean([r["signal_confidence"] for r in records])) if records else 0.0,
            }
        return results

    def find_underperforming(self, baseline_win_rate: float = 0.45, baseline_sharpe: float = 0.5) -> list[dict[str, Any]]:
        stats = self.analyze_by_strategy()
        underperforming = []
        for strategy, metrics in stats.items():
            if metrics["win_rate"] < baseline_win_rate:
                underperforming.append({
                    "strategy": strategy,
                    "issue": "low_win_rate",
                    "value": metrics["win_rate"],
                    "threshold": baseline_win_rate,
                })
        return underperforming

    def generate_recommendations(self) -> list[dict[str, Any]]:
        recommendations = []
        underperforming = self.find_underperforming()
        for item in underperforming:
            recommendations.append({
                "type": "reduce_weight",
                "target": item["strategy"],
                "reason": f"Win rate {item['value']:.2%} below threshold {item['threshold']:.2%}",
                "severity": "high" if item["value"] < 0.35 else "medium",
            })
        return recommendations
