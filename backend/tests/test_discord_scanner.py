from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from stradegy.engine.research.discord_scanner import DiscordScanner
from stradegy.engine.research.models import DiscordMention, SignalSource


class TestDiscordMention:
    def test_valid_creation(self):
        mention = DiscordMention(
            ticker_symbol="aapl",
            guild_id="123456789",
            channel_id="987654321",
            channel_name="stock-talk",
            message_id="msg001",
            message_url="https://discord.com/channels/123/987/msg001",
            content="AAPL to the moon!",
            created_utc=datetime.now(timezone.utc),
            score=42,
            num_reactions=15,
            reply_count=3,
            sentiment_compound=0.85,
            mention_count_1h=2,
            mention_count_6h=10,
            mention_count_24h=25,
            velocity_vs_avg=2.5,
            author="trader_joe",
        )
        assert mention.ticker_symbol == "AAPL"
        assert mention.channel_name == "stock-talk"
        assert mention.num_reactions == 15

    def test_invalid_negative_score(self):
        with pytest.raises(ValidationError):
            DiscordMention(
                ticker_symbol="AAPL",
                guild_id="123",
                channel_id="456",
                channel_name="test",
                message_id="abc",
                message_url="https://example.com",
                content="Test",
                created_utc=datetime.now(timezone.utc),
                score=-1,
                num_reactions=0,
                reply_count=0,
                sentiment_compound=0.0,
                mention_count_1h=0,
                mention_count_6h=0,
                mention_count_24h=0,
                velocity_vs_avg=1.0,
            )

    def test_sentiment_out_of_range(self):
        with pytest.raises(ValidationError):
            DiscordMention(
                ticker_symbol="AAPL",
                guild_id="123",
                channel_id="456",
                channel_name="test",
                message_id="abc",
                message_url="https://example.com",
                content="Test",
                created_utc=datetime.now(timezone.utc),
                score=0,
                num_reactions=0,
                reply_count=0,
                sentiment_compound=1.5,
                mention_count_1h=0,
                mention_count_6h=0,
                mention_count_24h=0,
                velocity_vs_avg=1.0,
            )

    def test_uppercase_ticker(self):
        mention = DiscordMention(
            ticker_symbol="tsla",
            guild_id="123",
            channel_id="456",
            channel_name="test",
            message_id="abc",
            message_url="https://example.com",
            content="Test",
            created_utc=datetime.now(timezone.utc),
            score=0,
            num_reactions=0,
            reply_count=0,
            sentiment_compound=0.0,
            mention_count_1h=0,
            mention_count_6h=0,
            mention_count_24h=0,
            velocity_vs_avg=0.0,
        )
        assert mention.ticker_symbol == "TSLA"


class TestDiscordScanner:
    def test_extract_tickers_basic(self):
        scanner = DiscordScanner()
        text = "I think $PLUG and AMD are great buys today"
        tickers = scanner.extract_tickers(text)
        assert "PLUG" in tickers
        assert "AMD" in tickers

    def test_extract_tickers_blacklist_filtered(self):
        scanner = DiscordScanner()
        text = "SPY is moving but PLUG is the real play"
        tickers = scanner.extract_tickers(text)
        assert "PLUG" in tickers
        assert "SPY" not in tickers

    def test_extract_tickers_no_matches(self):
        scanner = DiscordScanner()
        assert scanner.extract_tickers("No tickers here") == set()
        assert scanner.extract_tickers("") == set()

    def test_parse_ids_valid(self):
        scanner = DiscordScanner()
        ids = scanner._parse_ids("123, 456, 789")
        assert ids == [123, 456, 789]

    def test_parse_ids_empty(self):
        scanner = DiscordScanner()
        assert scanner._parse_ids("") == []
        assert scanner._parse_ids("   ") == []

    def test_parse_ids_invalid(self):
        scanner = DiscordScanner()
        with patch("stradegy.engine.research.discord_scanner.logger") as mock_logger:
            ids = scanner._parse_ids("123, abc, 456")
            assert ids == [123, 456]
            mock_logger.warning.assert_called_once()

    def test_build_message_url(self):
        scanner = DiscordScanner()
        url = scanner._build_message_url("123", "456", "789")
        assert url == "https://discord.com/channels/123/456/789"

    def test_analyze_message_no_tickers(self):
        scanner = DiscordScanner()
        msg = {
            "id": "1",
            "content": "Hello everyone",
            "timestamp": "2024-01-01T00:00:00.000Z",
            "author": {"username": "user1"},
            "reactions": [],
            "reply_count": 0,
            "flags": 0,
            "embeds": [],
        }
        channel = {"id": "456", "name": "general"}
        mentions = scanner._analyze_message(msg, channel)
        assert mentions == []

    def test_analyze_message_with_tickers(self):
        scanner = DiscordScanner()
        msg = {
            "id": "1",
            "content": "Buying more $PLUG today",
            "timestamp": "2024-01-01T00:00:00.000Z",
            "author": {"username": "user1"},
            "reactions": [{"count": 5, "emoji": {"name": "rocket"}}],
            "reply_count": 2,
            "flags": 0,
            "embeds": [],
        }
        channel = {"id": "456", "name": "stocks"}
        mentions = scanner._analyze_message(msg, channel)
        assert len(mentions) == 1
        assert mentions[0].ticker_symbol == "PLUG"
        assert mentions[0].channel_name == "stocks"
        assert mentions[0].num_reactions == 5
        assert mentions[0].reply_count == 2

    def test_analyze_message_with_embeds(self):
        scanner = DiscordScanner()
        msg = {
            "id": "1",
            "content": "Check this out",
            "timestamp": "2024-01-01T00:00:00.000Z",
            "author": {"username": "user1"},
            "reactions": [],
            "reply_count": 0,
            "flags": 0,
            "embeds": [
                {"title": "PLUG earnings beat", "description": "Great quarter for PLUG"}
            ],
        }
        channel = {"id": "456", "name": "news"}
        mentions = scanner._analyze_message(msg, channel)
        assert len(mentions) == 1
        assert mentions[0].ticker_symbol == "PLUG"
        assert "PLUG earnings beat" in mentions[0].content

    @pytest.mark.asyncio
    async def test_fetch_channel_messages_success(self):
        scanner = DiscordScanner()
        scanner.token = "fake_token"
        scanner.channel_ids = [123]
        scanner.client = AsyncMock()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "1",
                "content": "$AAPL is great",
                "timestamp": "2024-01-01T00:00:00.000Z",
                "author": {"username": "user1"},
                "reactions": [],
                "reply_count": 0,
                "flags": 0,
                "guild_id": "100",
                "embeds": [],
            }
        ]
        scanner.client.get.return_value = mock_response

        messages = await scanner._fetch_channel_messages(123, limit=10)
        assert len(messages) == 1
        assert messages[0]["channel_id"] == "123"
        scanner.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_channel_messages_rate_limit(self):
        scanner = DiscordScanner()
        scanner.token = "fake_token"
        scanner.channel_ids = [123]
        scanner.client = AsyncMock()

        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.json.return_value = {"retry_after": 0.1}

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = []

        scanner.client.get.side_effect = [rate_limited, success]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            messages = await scanner._fetch_channel_messages(123, limit=10)
            assert messages == []

    @pytest.mark.asyncio
    async def test_scan_recent_not_configured(self):
        scanner = DiscordScanner()
        scanner.token = ""
        scanner.channel_ids = []
        scanner.client = None
        mentions = await scanner.scan_recent(limit=10)
        assert mentions == []

    @pytest.mark.asyncio
    async def test_scan_hot_delegates_to_scan_recent(self):
        scanner = DiscordScanner()
        with patch.object(scanner, "scan_recent", new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = []
            await scanner.scan_hot(limit=50)
            mock_scan.assert_awaited_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_close(self):
        scanner = DiscordScanner()
        mock_client = AsyncMock()
        scanner.client = mock_client
        await scanner.close()
        mock_client.aclose.assert_awaited_once()
        assert scanner.client is None


class TestSignalSourceDiscord:
    def test_discord_enum_value(self):
        assert SignalSource.DISCORD == "discord"
