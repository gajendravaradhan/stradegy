from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from stradegy.engine.self_improvement.tracer import TradeTrace, TradeTracer
from stradegy.engine.strategy.reviewer import StrategyReviewer


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def reviewer(tmp_dir):
    with patch("stradegy.engine.strategy.reviewer.TradeTracer") as mock_tracer:
        mock_instance = TradeTracer(log_dir=tmp_dir)
        mock_tracer.return_value = mock_instance
        return StrategyReviewer()


def test_review_monthly_empty(reviewer):
    result = reviewer.review_monthly()
    assert result["period"] == "monthly"
    assert result["has_data"] is False
    assert result["strategies"] == []


def test_review_monthly_with_data(reviewer):
    for i in range(10):
        reviewer.tracer.append(TradeTrace(
            trade_id=f"t{i}",
            timestamp=datetime.now(),
            ticker="AAPL",
            action="buy",
            price=150.0,
            shares=10,
            strategy="MeanReversion",
            signal_confidence=0.8,
            pnl=10.0 if i < 7 else -5.0,
        ))

    result = reviewer.review_monthly()
    assert result["has_data"] is True
    assert len(result["strategies"]) == 1
    strategy = result["strategies"][0]
    assert strategy["name"] == "MeanReversion"
    assert strategy["total_trades"] == 10
    assert strategy["win_rate"] == 0.7


def test_review_quarterly_empty(reviewer):
    result = reviewer.review_quarterly()
    assert result["period"] == "quarterly"
    assert result["has_data"] is False
    assert result["strategies"] == []


def test_review_quarterly_with_data(reviewer):
    for i in range(20):
        reviewer.tracer.append(TradeTrace(
            trade_id=f"t{i}",
            timestamp=datetime.now(),
            ticker="AAPL",
            action="buy",
            price=150.0,
            shares=10,
            strategy="MomentumBreakout",
            signal_confidence=0.8,
            pnl=15.0 if i < 12 else -8.0,
        ))

    result = reviewer.review_quarterly()
    assert result["has_data"] is True
    assert len(result["strategies"]) == 1
    assert "midterm_goals" in result
    assert len(result["recommendations"]) > 0


def test_classify_performance(reviewer):
    assert reviewer._classify_performance(0.6, 1.5, 100) == "strong"
    assert reviewer._classify_performance(0.5, 0.8, 400) == "strong"
    assert reviewer._classify_performance(0.45, 0.5, 800) == "acceptable"
    assert reviewer._classify_performance(0.3, 0.1, 1200) == "weak"


def test_classify_performance_strict(reviewer):
    assert reviewer._classify_performance(0.6, 1.5, 100, strict=True) == "strong"
    assert reviewer._classify_performance(0.5, 0.8, 400, strict=True) == "acceptable"
    assert reviewer._classify_performance(0.44, 0.5, 800, strict=True) == "weak"


def test_generate_recommendations_weak(reviewer):
    strategies = [
        {"name": "MeanReversion", "status": "weak", "win_rate": 0.3, "sharpe": 0.1, "max_drawdown": 1500}
    ]
    recs = reviewer._generate_recommendations(strategies)
    assert len(recs) == 1
    assert recs[0]["type"] == "reduce_weight"
    assert recs[0]["severity"] == "high"


def test_generate_recommendations_acceptable_quarterly(reviewer):
    strategies = [
        {"name": "MomentumBreakout", "status": "acceptable", "win_rate": 0.45, "sharpe": 0.6, "max_drawdown": 800}
    ]
    recs = reviewer._generate_recommendations(strategies, quarterly=True)
    assert len(recs) == 1
    assert recs[0]["type"] == "tune_params"


def test_generate_recommendations_all_strong(reviewer):
    strategies = [
        {"name": "MeanReversion", "status": "strong", "win_rate": 0.6, "sharpe": 1.2, "max_drawdown": 200},
        {"name": "MomentumBreakout", "status": "strong", "win_rate": 0.55, "sharpe": 1.0, "max_drawdown": 300},
    ]
    recs = reviewer._generate_recommendations(strategies)
    assert len(recs) == 1
    assert recs[0]["type"] == "increase_risk"


def test_calculate_sharpe(reviewer):
    assert reviewer._calculate_sharpe([]) == 0.0
    assert reviewer._calculate_sharpe([10.0]) == 0.0
    pnls = [10.0, -5.0, 15.0, -10.0, 20.0]
    sharpe = reviewer._calculate_sharpe(pnls)
    assert isinstance(sharpe, float)
    assert sharpe != 0.0


def test_calculate_max_drawdown(reviewer):
    assert reviewer._calculate_max_drawdown([]) == 0.0
    pnls = [10.0, -5.0, 15.0, -20.0, 5.0]
    max_dd = reviewer._calculate_max_drawdown(pnls)
    assert isinstance(max_dd, float)
    assert max_dd >= 0.0


def test_generate_midterm_goals(reviewer):
    strategies = [
        {"name": "S1", "win_rate": 0.45, "sharpe": 0.8},
        {"name": "S2", "win_rate": 0.40, "sharpe": 0.9},
    ]
    goals = reviewer._generate_midterm_goals(strategies)
    assert len(goals) == 3
    assert any("win rate" in g["goal"].lower() for g in goals)
    assert any("Sharpe" in g["goal"] for g in goals)


def test_record_baseline(reviewer):
    metrics = {
        "sharpe": 1.2,
        "sortino": 1.0,
        "calmar": 0.8,
        "max_drawdown": 0.05,
        "win_rate": 0.6,
        "total_trades": 100,
        "total_return": 0.15,
    }
    reviewer.record_baseline(metrics)
    latest = reviewer.metrics.latest()
    assert latest is not None
    assert latest.sharpe == 1.2
    assert latest.win_rate == 0.6
