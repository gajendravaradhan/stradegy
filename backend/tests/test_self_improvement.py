import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from stradegy.engine.self_improvement.analyzer import TraceAnalyzer
from stradegy.engine.self_improvement.metrics import BaselineSnapshot, MetricsBaseline
from stradegy.engine.self_improvement.ratchet import RatchetLoop
from stradegy.engine.self_improvement.skillbook import Skill, Skillbook
from stradegy.engine.self_improvement.tracer import TradeTrace, TradeTracer
from stradegy.engine.self_improvement.versioning import StrategyVersion, VersionManager


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def tracer(tmp_dir):
    return TradeTracer(log_dir=tmp_dir)


@pytest.fixture
def analyzer(tmp_dir):
    return TraceAnalyzer(TradeTracer(log_dir=tmp_dir))


@pytest.fixture
def skillbook(tmp_dir):
    return Skillbook(path=tmp_dir / "skillbook.jsonl")


@pytest.fixture
def baseline(tmp_dir):
    return MetricsBaseline(path=tmp_dir / "baseline.jsonl")


@pytest.fixture
def version_manager(tmp_dir):
    return VersionManager(path=tmp_dir / "versions.jsonl")


@pytest.fixture
def ratchet(baseline, skillbook, version_manager):
    return RatchetLoop(baseline, skillbook, version_manager)


def test_trade_tracer_append_and_get(tracer):
    trace = TradeTrace(
        trade_id="t1",
        timestamp=datetime.now(),
        ticker="AAPL",
        action="buy",
        price=150.0,
        shares=10,
        strategy="MeanReversion",
        signal_confidence=0.8,
        pnl=25.0,
    )
    tracer.append(trace)
    recent = tracer.get_recent(n=10)
    assert len(recent) == 1
    assert recent[0]["ticker"] == "AAPL"


def test_trade_tracer_get_by_strategy(tracer):
    for i in range(5):
        tracer.append(TradeTrace(
            trade_id=f"t{i}",
            timestamp=datetime.now(),
            ticker="AAPL",
            action="buy",
            price=150.0,
            shares=10,
            strategy="MeanReversion",
            signal_confidence=0.8,
            pnl=10.0,
        ))
    tracer.append(TradeTrace(
        trade_id="t5",
        timestamp=datetime.now(),
        ticker="MSFT",
        action="buy",
        price=300.0,
        shares=5,
        strategy="MomentumBreakout",
        signal_confidence=0.7,
        pnl=-5.0,
    ))
    mr = tracer.get_by_strategy("MeanReversion")
    assert len(mr) == 5
    mb = tracer.get_by_strategy("MomentumBreakout")
    assert len(mb) == 1


def test_analyzer_empty(analyzer):
    stats = analyzer.analyze_by_strategy()
    assert stats == {}


def test_analyzer_by_strategy(analyzer):
    for i in range(4):
        analyzer.tracer.append(TradeTrace(
            trade_id=f"w{i}",
            timestamp=datetime.now(),
            ticker="AAPL",
            action="buy",
            price=150.0,
            shares=10,
            strategy="MeanReversion",
            signal_confidence=0.8,
            pnl=10.0 if i < 3 else -5.0,
        ))
    stats = analyzer.analyze_by_strategy(days=30)
    assert "MeanReversion" in stats
    assert stats["MeanReversion"]["total_trades"] == 4
    assert stats["MeanReversion"]["win_rate"] == 0.75


def test_analyzer_recommendations(analyzer):
    for i in range(10):
        analyzer.tracer.append(TradeTrace(
            trade_id=f"l{i}",
            timestamp=datetime.now(),
            ticker="AAPL",
            action="buy",
            price=150.0,
            shares=10,
            strategy="MeanReversion",
            signal_confidence=0.5,
            pnl=-5.0,
        ))
    recs = analyzer.generate_recommendations()
    assert len(recs) > 0
    assert recs[0]["type"] == "reduce_weight"
    assert recs[0]["target"] == "MeanReversion"


def test_skillbook_add_and_get(skillbook):
    skill = Skill(
        name="MeanReversion_v1",
        strategy_params={"rsi_period": 14},
        quality_gates={"sharpe": 0.5},
        score=0.8,
    )
    skillbook.add(skill)
    retrieved = skillbook.get("MeanReversion_v1")
    assert retrieved is not None
    assert retrieved.score == 0.8


def test_skillbook_evaluate(skillbook):
    skill = Skill(
        name="Test",
        strategy_params={},
        quality_gates={"sharpe": 0.5, "win_rate": 0.45},
    )
    skillbook.add(skill)
    assert skillbook.evaluate("Test", {"sharpe": 0.6, "win_rate": 0.5}) is True
    assert skillbook.evaluate("Test", {"sharpe": 0.4, "win_rate": 0.5}) is False


def test_skillbook_promote_demote(skillbook):
    skill = Skill(name="S1", strategy_params={}, quality_gates={}, score=0.5)
    skillbook.add(skill)
    skillbook.demote("S1")
    assert skillbook.get("S1").is_active is False
    skillbook.promote("S1", 0.9)
    assert skillbook.get("S1").is_active is True
    assert skillbook.get("S1").score == 0.9


def test_metrics_record_and_latest(baseline):
    snap = BaselineSnapshot(
        date="2025-01-01",
        sharpe=1.2,
        sortino=1.0,
        calmar=0.8,
        max_drawdown=0.05,
        win_rate=0.6,
        total_trades=100,
        total_return=0.15,
    )
    baseline.record(snap)
    latest = baseline.latest()
    assert latest is not None
    assert latest.sharpe == 1.2


def test_metrics_compare(baseline):
    baseline.record(BaselineSnapshot(
        date="2025-01-01",
        sharpe=1.0,
        sortino=0.8,
        calmar=0.6,
        max_drawdown=0.10,
        win_rate=0.5,
        total_trades=100,
        total_return=0.10,
    ))
    result = baseline.compare({"sharpe": 1.2, "sortino": 0.9, "calmar": 0.5, "win_rate": 0.55, "total_return": 0.12})
    assert result["is_improved"] is True


def test_metrics_regression(baseline):
    baseline.record(BaselineSnapshot(
        date="2025-01-01",
        sharpe=1.0,
        sortino=0.8,
        calmar=0.6,
        max_drawdown=0.10,
        win_rate=0.5,
        total_trades=100,
        total_return=0.10,
    ))
    assert baseline.is_regression({"sharpe": 0.5, "max_drawdown": 0.20}) is True
    assert baseline.is_regression({"sharpe": 1.1, "max_drawdown": 0.05}) is False


def test_version_manager_save_and_list(version_manager):
    v1 = StrategyVersion(
        version_id="v1",
        timestamp=datetime.now().isoformat(),
        strategy_name="MeanReversion",
        params={"rsi": 14},
        metrics={},
    )
    version_manager.save(v1)
    versions = version_manager.list_versions("MeanReversion")
    assert len(versions) == 1
    assert version_manager.get_latest("MeanReversion").version_id == "v1"


def test_version_manager_rollback(version_manager):
    v1 = StrategyVersion(
        version_id="v1",
        timestamp=datetime.now().isoformat(),
        strategy_name="MeanReversion",
        params={"rsi": 14},
        metrics={},
    )
    v2 = StrategyVersion(
        version_id="v2",
        timestamp=datetime.now().isoformat(),
        strategy_name="MeanReversion",
        params={"rsi": 21},
        metrics={},
    )
    version_manager.save(v1)
    version_manager.save(v2)
    params = version_manager.rollback_params("MeanReversion")
    assert params == {"rsi": 21}
    params = version_manager.rollback_params("MeanReversion", version_id="v1")
    assert params == {"rsi": 14}


def test_ratchet_propose(ratchet):
    proposal = ratchet.propose_change("MeanReversion", {"weight": 0.4})
    assert "version_id" in proposal
    assert proposal["params"]["weight"] == 0.4


def test_ratchet_keep(ratchet):
    proposal = ratchet.propose_change("MeanReversion", {"weight": 0.4})
    metrics = {"sharpe": 1.5, "max_drawdown": 0.05, "win_rate": 0.6, "total_return": 0.2, "total_trades": 50}
    evaluation = ratchet.evaluate_change(proposal["version_id"], metrics)
    decision = ratchet.keep_or_revert(evaluation)
    assert decision["action"] == "keep"
    assert ratchet.baseline.latest() is not None


def test_ratchet_revert(ratchet):
    ratchet.baseline.record(BaselineSnapshot(
        date="2025-01-01",
        sharpe=1.0,
        sortino=0.8,
        calmar=0.6,
        max_drawdown=0.05,
        win_rate=0.5,
        total_trades=100,
        total_return=0.10,
    ))
    proposal = ratchet.propose_change("MeanReversion", {"weight": 0.4})
    metrics = {"sharpe": 0.3, "max_drawdown": 0.30, "win_rate": 0.2, "total_return": -0.1, "total_trades": 10}
    evaluation = ratchet.evaluate_change(proposal["version_id"], metrics)
    decision = ratchet.keep_or_revert(evaluation)
    assert decision["action"] == "revert"
