from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from stradegy.engine.research.reddit_scanner import RedditScanner
from stradegy.engine.research.models import RedditMention


class TestRedditScanner:
    def test_extract_tickers_basic(self):
        scanner = RedditScanner()
        text = "I think $PLUG and AMD are great buys today"
        tickers = scanner.extract_tickers(text)
        assert "PLUG" in tickers
        assert "AMD" in tickers

    def test_extract_tickers_blacklist_filtered(self):
        scanner = RedditScanner()
        text = "SPY is moving but PLUG is the real play"
        tickers = scanner.extract_tickers(text)
        assert "PLUG" in tickers
        assert "SPY" not in tickers

    def test_extract_tickers_no_matches(self):
        scanner = RedditScanner()
        assert scanner.extract_tickers("No tickers here") == set()
        assert scanner.extract_tickers("") == set()

    def test_parse_post_no_tickers(self):
        scanner = RedditScanner()
        post = {
            "title": "Hello everyone",
            "selftext": "Just saying hi",
            "score": 10,
            "num_comments": 2,
            "upvote_ratio": 0.95,
            "created_utc": 1700000000.0,
            "permalink": "/r/wsb/comments/abc/test/",
            "id": "abc123",
            "subreddit": "wallstreetbets",
            "author": "user1",
        }
        mentions = scanner._parse_post(post)
        assert mentions == []

    def test_parse_post_with_tickers(self):
        scanner = RedditScanner()
        post = {
            "title": "Buying more $PLUG today",
            "selftext": "PLUG to the moon",
            "score": 150,
            "num_comments": 42,
            "upvote_ratio": 0.85,
            "created_utc": 1700000000.0,
            "permalink": "/r/wsb/comments/abc/test/",
            "id": "abc123",
            "subreddit": "wallstreetbets",
            "author": "trader_joe",
        }
        mentions = scanner._parse_post(post)
        assert len(mentions) == 1
        assert mentions[0].ticker_symbol == "PLUG"
        assert mentions[0].subreddit == "wallstreetbets"
        assert mentions[0].score == 150
        assert mentions[0].num_comments == 42
        assert mentions[0].author == "trader_joe"

    @pytest.mark.asyncio
    async def test_fetch_subreddit_success(self):
        scanner = RedditScanner()
        scanner.client = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "children": [
                    {"data": {"title": "$PLUG moon", "id": "1"}},
                    {"data": {"title": "No tickers", "id": "2"}},
                ]
            }
        }
        scanner.client.get.return_value = mock_resp

        posts = await scanner._fetch_subreddit("wallstreetbets", "hot", 10)
        assert len(posts) == 2
        assert posts[0]["title"] == "$PLUG moon"
        scanner.client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_subreddit_rate_limit(self):
        scanner = RedditScanner()
        scanner.client = AsyncMock()

        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"data": {"children": []}}

        scanner.client.get.side_effect = [rate_limited, success]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            posts = await scanner._fetch_subreddit("wallstreetbets", "hot", 10)
            assert posts == []
            assert scanner.client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_fetch_subreddit_blocked(self):
        scanner = RedditScanner()
        scanner.client = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        scanner.client.get.return_value = mock_resp

        posts = await scanner._fetch_subreddit("wallstreetbets", "hot", 10)
        assert posts == []

    @pytest.mark.asyncio
    async def test_scan_hot(self):
        scanner = RedditScanner()
        mock_posts = [
            {"title": "$PLUG is great", "selftext": "", "score": 100, "num_comments": 10, "upvote_ratio": 0.9, "created_utc": 1700000000.0, "permalink": "/r/wsb/1", "id": "1", "subreddit": "wallstreetbets", "author": "u1"},
        ]
        with patch.object(scanner, "_fetch_subreddit", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_posts
            mentions = await scanner.scan_hot(limit=10)
            assert len(mentions) == len(scanner.SUBREDDITS)
            assert mentions[0].ticker_symbol == "PLUG"
            assert mock_fetch.await_count == len(scanner.SUBREDDITS)

    @pytest.mark.asyncio
    async def test_scan_recent(self):
        scanner = RedditScanner()
        mock_posts = [
            {"title": "AMD earnings", "selftext": "", "score": 200, "num_comments": 50, "upvote_ratio": 0.95, "created_utc": 1700000000.0, "permalink": "/r/stocks/1", "id": "2", "subreddit": "stocks", "author": "u2"},
        ]
        with patch.object(scanner, "_fetch_subreddit", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_posts
            mentions = await scanner.scan_recent(limit=10)
            assert len(mentions) == len(scanner.SUBREDDITS)
            assert mentions[0].ticker_symbol == "AMD"

    @pytest.mark.asyncio
    async def test_close(self):
        scanner = RedditScanner()
        mock_client = AsyncMock()
        scanner.client = mock_client
        await scanner.close()
        mock_client.aclose.assert_awaited_once()
        assert scanner.client is None
