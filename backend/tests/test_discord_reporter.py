from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stradegy.engine.research.discord_reporter import DiscordReporter


class TestDiscordReporter:
    def test_init_not_configured(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = ""
            mock_settings.discord_general_channel_id = ""
            reporter = DiscordReporter()
            assert reporter._client is None
            assert reporter._ensure_client() is False

    def test_init_configured(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            assert reporter._client is not None
            assert reporter._ensure_client() is True

    @pytest.mark.asyncio
    async def test_send_to_channel_success(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            reporter._client.post.return_value = mock_resp

            success = await reporter._send_to_channel(content="Hello", embed={"title": "Test"})
            assert success is True
            reporter._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_to_channel_rate_limit_retry(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            rate_limited = MagicMock()
            rate_limited.status_code = 429
            rate_limited.json.return_value = {"retry_after": 0.1}

            success_resp = MagicMock()
            success_resp.status_code = 200

            reporter._client.post.side_effect = [rate_limited, success_resp]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await reporter._send_to_channel(content="Hello")
                assert result is True
                assert reporter._client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_send_to_channel_failure(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            reporter._client.post.return_value = mock_resp

            success = await reporter._send_to_channel(content="Hello")
            assert success is False

    @pytest.mark.asyncio
    async def test_send_daily_report_success(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            reporter._client.post.return_value = mock_resp

            data = {
                "equity": 10000.0,
                "day_pnl": 250.0,
                "day_pnl_pct": 0.025,
                "open_positions": 2,
                "positions": [
                    {"symbol": "AAPL", "qty": 10, "unrealized_plpc": 0.05, "pnl": 150.0},
                ],
                "gems_found": 3,
                "mode": "paper",
                "strategy_insights": ["Mean Reversion performed well today"],
            }
            result = await reporter.send_daily_report(data)
            assert result is True
            reporter._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_monthly_report_success(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            reporter._client.post.return_value = mock_resp

            data = {
                "total_return": 5.5,
                "sharpe": 1.2,
                "max_drawdown": 0.03,
                "win_rate": 0.55,
                "total_trades": 45,
                "best_performer": "AAPL ($500.00)",
                "worst_performer": "TSLA (-$200.00)",
                "adjustments": ["Reduce Mean Reversion weight"],
            }
            result = await reporter.send_monthly_report(data)
            assert result is True
            reporter._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_quarterly_report_success(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            reporter._client.post.return_value = mock_resp

            data = {
                "total_return": 12.0,
                "annualized_return": 48.0,
                "sharpe": 1.5,
                "max_drawdown": 0.05,
                "win_rate": 0.58,
                "strategy_changes": ["Increase momentum weight"],
                "midterm_goals": ["Achieve Sharpe ratio of 1.0+"],
            }
            result = await reporter.send_quarterly_report(data)
            assert result is True
            reporter._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_moonshot_alert_success(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            reporter._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            reporter._client.post.return_value = mock_resp

            gem_data = {
                "ticker": "PLUG",
                "score": 92,
                "classification": "strong_gem",
                "catalyst": "Earnings beat with 200% revenue growth",
                "urgency": "critical",
            }
            result = await reporter.send_moonshot_alert(gem_data)
            assert result is True
            reporter._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_daily_report_no_client(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = ""
            mock_settings.discord_general_channel_id = ""
            reporter = DiscordReporter()
            result = await reporter.send_daily_report({"equity": 10000.0})
            assert result is False

    @pytest.mark.asyncio
    async def test_close(self):
        with patch("stradegy.engine.research.discord_reporter.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_general_channel_id = "12345"
            reporter = DiscordReporter()
            mock_client = AsyncMock()
            reporter._client = mock_client
            await reporter.close()
            mock_client.aclose.assert_awaited_once()
            assert reporter._client is None
