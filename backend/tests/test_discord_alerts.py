from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stradegy.engine.research.discord_alerts import DiscordAlertManager
from stradegy.engine.research.models import GemClassification, GemSignal


class TestDiscordAlertManager:
    def test_init_not_configured(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = ""
            mock_settings.discord_user_id = ""
            mgr = DiscordAlertManager()
            assert mgr._client is None
            assert mgr._ensure_client() is False

    def test_init_configured(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            assert mgr._client is not None
            assert mgr._ensure_client() is True

    @pytest.mark.asyncio
    async def test_get_dm_channel_cached(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._dm_channel_id = "cached_456"
            channel_id = await mgr._get_dm_channel()
            assert channel_id == "cached_456"

    @pytest.mark.asyncio
    async def test_get_dm_channel_create_success(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"id": "789"}
            mgr._client.post.return_value = mock_resp

            channel_id = await mgr._get_dm_channel()
            assert channel_id == "789"
            assert mgr._dm_channel_id == "789"
            mgr._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_dm_channel_create_failure(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.text = "Forbidden"
            mgr._client.post.return_value = mock_resp

            channel_id = await mgr._get_dm_channel()
            assert channel_id is None

    @pytest.mark.asyncio
    async def test_send_to_channel_success(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mgr._client.post.return_value = mock_resp

            success = await mgr._send_to_channel("456", content="Hello", embed={"title": "Test"})
            assert success is True
            mgr._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_to_channel_rate_limit_retry(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()

            rate_limited = MagicMock()
            rate_limited.status_code = 429
            rate_limited.json.return_value = {"retry_after": 0.1}

            success_resp = MagicMock()
            success_resp.status_code = 200

            mgr._client.post.side_effect = [rate_limited, success_resp]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await mgr._send_to_channel("456", content="Hello")
                assert result is True
                assert mgr._client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_send_to_channel_no_client(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = ""
            mock_settings.discord_user_id = ""
            mgr = DiscordAlertManager()
            success = await mgr._send_to_channel("456", content="Hello")
            assert success is False

    @pytest.mark.asyncio
    async def test_send_dm_success(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "789"

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mgr._client.post.return_value = mock_resp

            success = await mgr._send_dm(content="Hello DM")
            assert success is True

    def test_is_urgent_high_score_many_sources(self):
        with patch("stradegy.engine.research.discord_alerts.settings"):
            mgr = DiscordAlertManager()
            gem = GemSignal(
                ticker_symbol="AAPL",
                reddit_score=20,
                discord_score=10,
                sec_score=25,
                news_score=15,
                technical_score=20,
                total_score=90,
                source_count=3,
            )
            assert mgr._is_urgent(gem) is True

    def test_is_urgent_medium_score(self):
        with patch("stradegy.engine.research.discord_alerts.settings"):
            mgr = DiscordAlertManager()
            gem = GemSignal(
                ticker_symbol="AAPL",
                reddit_score=20,
                discord_score=10,
                sec_score=25,
                news_score=15,
                technical_score=20,
                total_score=70,
                source_count=2,
            )
            assert mgr._is_urgent(gem) is False

    def test_is_urgent_cross_signal(self):
        with patch("stradegy.engine.research.discord_alerts.settings"):
            mgr = DiscordAlertManager()
            gem = GemSignal(
                ticker_symbol="AAPL",
                reddit_score=25,
                discord_score=20,
                sec_score=10,
                news_score=20,
                technical_score=10,
                total_score=85,
                source_count=3,
            )
            assert mgr._is_urgent(gem) is True

    @pytest.mark.asyncio
    async def test_send_gem_alert_not_configured(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = ""
            mock_settings.discord_user_id = ""
            mgr = DiscordAlertManager()
            gem = GemSignal(ticker_symbol="AAPL", reddit_score=20, discord_score=10, sec_score=25, news_score=15, technical_score=20)
            result = await mgr.send_gem_alert(gem)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_gem_alert_success(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mock_settings.discord_general_channel_id = "999"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "456"

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mgr._client.post.return_value = mock_resp

            gem = GemSignal(
                ticker_symbol="PLUG",
                reddit_score=20,
                discord_score=10,
                sec_score=25,
                news_score=15,
                technical_score=20,
                total_score=70,
                source_count=2,
                evidence_urls=["https://example.com/1", "https://example.com/2"],
            )
            result = await mgr.send_gem_alert(gem)
            assert result is True
            assert "PLUG" in mgr._last_alert

    @pytest.mark.asyncio
    async def test_send_gem_alert_urgent_to_dm(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "456"

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mgr._client.post.return_value = mock_resp

            gem = GemSignal(
                ticker_symbol="TSLA",
                reddit_score=25,
                discord_score=15,
                sec_score=25,
                news_score=15,
                technical_score=20,
                total_score=100,
                source_count=3,
            )
            result = await mgr.send_gem_alert(gem)
            assert result is True
            mgr._client.post.assert_awaited_once()
            call_args = mgr._client.post.await_args
            assert "456" in str(call_args[0][0])

    @pytest.mark.asyncio
    async def test_send_gem_alert_throttled(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "456"
            mgr._last_alert["PLUG"] = datetime.now(timezone.utc)

            gem = GemSignal(ticker_symbol="PLUG", reddit_score=20, discord_score=10, sec_score=25, news_score=15, technical_score=20)
            result = await mgr.send_gem_alert(gem)
            assert result is False
            mgr._client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_trade_notification(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mock_settings.discord_general_channel_id = "999"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "456"

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mgr._client.post.return_value = mock_resp

            trade = {
                "side": "buy",
                "symbol": "PLUG",
                "qty": 100,
                "price": 5.50,
                "total": 550.0,
            }
            result = await mgr.send_trade_notification(trade)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_risk_alert(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "456"

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mgr._client.post.return_value = mock_resp

            data = {
                "emergencies": ["DRAWDOWN: 25.0% exceeds limit", "PDT: Day trade limit reached"],
                "drawdown_status": {"drawdown": 0.25, "limit": 0.20},
                "pdt_status": {"pdt_count": 3, "pdt_limit": 3},
            }
            result = await mgr.send_risk_alert(data)
            assert result is True

    @pytest.mark.asyncio
    async def test_send_risk_alert_no_emergencies(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mgr._client = AsyncMock()
            mgr._dm_channel_id = "456"

            data = {"emergencies": []}
            result = await mgr.send_risk_alert(data)
            assert result is False
            mgr._client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_close(self):
        with patch("stradegy.engine.research.discord_alerts.settings") as mock_settings:
            mock_settings.discord_bot_token = "fake_token"
            mock_settings.discord_user_id = "12345"
            mgr = DiscordAlertManager()
            mock_client = AsyncMock()
            mgr._client = mock_client
            await mgr.close()
            mock_client.aclose.assert_awaited_once()
            assert mgr._client is None
