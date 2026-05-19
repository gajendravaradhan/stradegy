import pytest

from stradegy.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.app_name == "Stradegy"
    assert settings.app_version == "2.0.0"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8420
    assert settings.paper_trading is True
    assert settings.autonomy_mode == "semi"
    assert settings.max_drawdown == 0.20
    assert settings.risk_per_trade == 0.03
    assert settings.max_positions == 1


def test_alpaca_paper_url():
    settings = Settings(paper_trading=True)
    assert settings.alpaca_base_url == "https://paper-api.alpaca.markets"


def test_alpaca_live_url():
    settings = Settings(paper_trading=False)
    assert settings.alpaca_base_url == "https://api.alpaca.markets"


def test_database_url():
    settings = Settings()
    assert settings.database_url.startswith("sqlite+aiosqlite://")
