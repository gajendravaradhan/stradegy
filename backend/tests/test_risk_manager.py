import pytest
from datetime import date, timedelta

from stradegy.engine.risk.manager import RiskManager


@pytest.fixture
def rm():
    return RiskManager()


def test_calculate_position_size_basic(rm):
    result = rm.calculate_position_size(equity=10000, atr=2.0, price=100)
    assert result["shares"] > 0
    assert result["position_value"] > 0
    assert result["stop_loss"] > 0
    assert result["stop_distance"] == pytest.approx(3.0, abs=0.01)
    assert result["risk_amount"] == pytest.approx(300.0, abs=0.01)
    assert result["risk_pct"] > 0


def test_calculate_position_size_max_cap(rm):
    result = rm.calculate_position_size(equity=10000, atr=0.1, price=10)
    assert result["shares"] <= 250
    assert result["position_value"] <= 2500


def test_calculate_position_size_zero_inputs(rm):
    result = rm.calculate_position_size(equity=10000, atr=0, price=100)
    assert result["shares"] == 0
    assert result["stop_loss"] == 0
    assert result["risk_amount"] == 0


def test_calculate_position_size_negative_price(rm):
    result = rm.calculate_position_size(equity=10000, atr=2.0, price=-5)
    assert result["shares"] == 0


def test_check_drawdown_safe(rm):
    result = rm.check_drawdown(equity=10000, peak_equity=10000)
    assert result["is_safe"] is True
    assert result["drawdown"] == 0.0
    assert result["kill_switch"] is False


def test_check_drawdown_warning(rm):
    result = rm.check_drawdown(equity=9000, peak_equity=10000)
    assert result["is_safe"] is True
    assert result["drawdown"] == pytest.approx(0.10, abs=0.01)
    assert result["kill_switch"] is False


def test_check_drawdown_kill_switch(rm):
    result = rm.check_drawdown(equity=7500, peak_equity=10000)
    assert result["is_safe"] is False
    assert result["drawdown"] == pytest.approx(0.25, abs=0.01)
    assert result["kill_switch"] is True


def test_check_drawdown_zero_peak(rm):
    result = rm.check_drawdown(equity=10000, peak_equity=0)
    assert result["is_safe"] is True
    assert result["drawdown"] == 0.0


def test_check_pdt_safe(rm):
    trades = [date.today() - timedelta(days=1), date.today() - timedelta(days=2)]
    result = rm.check_pdt(trades)
    assert result["pdt_count"] == 2
    assert result["pdt_remaining"] == 1
    assert result["pdt_violation"] is False
    assert result["can_trade"] is True


def test_check_pdt_at_limit(rm):
    trades = [date.today() - timedelta(days=i) for i in range(3)]
    result = rm.check_pdt(trades)
    assert result["pdt_count"] == 3
    assert result["pdt_remaining"] == 0
    assert result["pdt_violation"] is True
    assert result["can_trade"] is False


def test_check_pdt_old_trades_ignored(rm):
    trades = [date.today() - timedelta(days=10)]
    result = rm.check_pdt(trades)
    assert result["pdt_count"] == 0
    assert result["can_trade"] is True


def test_calculate_tax_reserve(rm):
    result = rm.calculate_tax_reserve(realized_gains=1000)
    assert result["realized_gains"] == 1000
    assert result["tax_owed"] == pytest.approx(300.0, abs=0.01)
    assert result["reserve_required"] == pytest.approx(300.0, abs=0.01)


def test_calculate_tax_reserve_zero_gains(rm):
    result = rm.calculate_tax_reserve(realized_gains=0)
    assert result["tax_owed"] == 0


def test_check_correlation(rm):
    corr = {
        "AAPL": {"AAPL": 1.0, "MSFT": 0.85},
        "MSFT": {"AAPL": 0.85, "MSFT": 1.0},
    }
    warnings = rm.check_correlation(corr, threshold=0.8)
    assert len(warnings) == 1
    assert "AAPL-MSFT" in warnings[0]


def test_check_correlation_no_warnings(rm):
    corr = {
        "AAPL": {"AAPL": 1.0, "MSFT": 0.5},
        "MSFT": {"AAPL": 0.5, "MSFT": 1.0},
    }
    warnings = rm.check_correlation(corr, threshold=0.8)
    assert warnings == []


def test_emergency_check_none(rm):
    pdt_data = {"pdt_violation": False, "pdt_count": 0}
    result = rm.emergency_check(equity=10000, peak_equity=10000, pdt_data=pdt_data, correlation_warnings=[])
    assert result["is_emergency"] is False
    assert result["should_halt_trading"] is False


def test_emergency_check_drawdown(rm):
    pdt_data = {"pdt_violation": False}
    result = rm.emergency_check(equity=7000, peak_equity=10000, pdt_data=pdt_data, correlation_warnings=[])
    assert result["is_emergency"] is True
    assert result["should_halt_trading"] is True
    assert any("DRAWDOWN" in e for e in result["emergencies"])


def test_emergency_check_pdt(rm):
    pdt_data = {"pdt_violation": True}
    result = rm.emergency_check(equity=10000, peak_equity=10000, pdt_data=pdt_data, correlation_warnings=[])
    assert result["is_emergency"] is True
    assert result["should_halt_trading"] is True
    assert any("PDT" in e for e in result["emergencies"])
