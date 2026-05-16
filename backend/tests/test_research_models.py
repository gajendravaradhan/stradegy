from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from stradegy.engine.research.models import (
    GemClassification,
    GemSignal,
    NewsArticle,
    RedditMention,
    SECFiling,
    SignalSource,
    SourceScore,
    TechnicalScore,
    ValidationResult,
)


class TestSignalSource:
    def test_enum_values(self):
        assert SignalSource.REDDIT == "reddit"
        assert SignalSource.DISCORD == "discord"
        assert SignalSource.SEC == "sec"
        assert SignalSource.NEWS == "news"
        assert SignalSource.TECHNICAL == "technical"


class TestRedditMention:
    def test_valid_creation(self):
        mention = RedditMention(
            ticker_symbol="aapl",
            subreddit="wallstreetbets",
            post_id="abc123",
            post_url="https://reddit.com/r/wsb/abc123",
            title="AAPL to the moon",
            created_utc=datetime.now(timezone.utc),
            score=150,
            num_comments=42,
            upvote_ratio=0.85,
            sentiment_compound=0.75,
            mention_count_1h=5,
            mention_count_6h=20,
            mention_count_24h=50,
            velocity_vs_avg=3.5,
        )
        assert mention.ticker_symbol == "AAPL"
        assert mention.score == 150

    def test_invalid_negative_score(self):
        with pytest.raises(ValidationError):
            RedditMention(
                ticker_symbol="AAPL",
                subreddit="wsb",
                post_id="abc",
                post_url="https://example.com",
                title="Test",
                created_utc=datetime.now(timezone.utc),
                score=-1,
                num_comments=0,
                upvote_ratio=0.5,
                sentiment_compound=0.0,
                mention_count_1h=0,
                mention_count_6h=0,
                mention_count_24h=0,
                velocity_vs_avg=1.0,
            )

    def test_sentiment_out_of_range(self):
        with pytest.raises(ValidationError):
            RedditMention(
                ticker_symbol="AAPL",
                subreddit="wsb",
                post_id="abc",
                post_url="https://example.com",
                title="Test",
                created_utc=datetime.now(timezone.utc),
                score=0,
                num_comments=0,
                upvote_ratio=0.5,
                sentiment_compound=1.5,
                mention_count_1h=0,
                mention_count_6h=0,
                mention_count_24h=0,
                velocity_vs_avg=1.0,
            )


class TestSECFiling:
    def test_valid_creation(self):
        filing = SECFiling(
            ticker_symbol="tsla",
            filing_type="10-K",
            filing_date=datetime.now(timezone.utc),
            filing_url="https://sec.gov/...",
            revenue_growth_yoy=0.25,
            gross_margin=0.18,
            insider_net_buys=3,
        )
        assert filing.ticker_symbol == "TSLA"
        assert filing.filing_type == "10-K"


class TestNewsArticle:
    def test_valid_creation(self):
        article = NewsArticle(
            ticker_symbol="nvda",
            headline="NVDA beats earnings",
            article_url="https://example.com/news",
            source="Bloomberg",
            published_at=datetime.now(timezone.utc),
            finbert_sentiment=0.85,
            finbert_confidence=0.92,
            finbert_label="positive",
        )
        assert article.ticker_symbol == "NVDA"
        assert article.finbert_label == "positive"

    def test_finbert_out_of_range(self):
        with pytest.raises(ValidationError):
            NewsArticle(
                ticker_symbol="NVDA",
                headline="Test",
                article_url="https://example.com",
                source="Test",
                published_at=datetime.now(timezone.utc),
                finbert_sentiment=1.5,
                finbert_confidence=0.5,
                finbert_label="positive",
            )


class TestTechnicalScore:
    def test_passes_all_filters(self):
        score = TechnicalScore(
            ticker_symbol="amd",
            price=150.0,
            price_vs_sma15=1.02,
            price_vs_20day_high=0.98,
            volume_vs_50day_avg=2.5,
            market_cap_millions=150000,
            rsi_14=45,
            passes_price_filter=True,
            passes_volume_filter=True,
            passes_market_cap_filter=True,
            passes_rsi_filter=True,
            overall_pass=True,
        )
        assert score.ticker_symbol == "AMD"
        assert score.overall_pass is True

    def test_rsi_bounds(self):
        with pytest.raises(ValidationError):
            TechnicalScore(
                ticker_symbol="AMD",
                price=150.0,
                price_vs_sma15=1.0,
                price_vs_20day_high=1.0,
                volume_vs_50day_avg=1.0,
                rsi_14=150,
                passes_price_filter=True,
                passes_volume_filter=True,
                passes_market_cap_filter=True,
                passes_rsi_filter=True,
                overall_pass=True,
            )


class TestSourceScore:
    def test_weighted_score_calculation(self):
        source = SourceScore(
            source=SignalSource.REDDIT,
            raw_score=80.0,
            weight=0.25,
            weighted_score=20.0,
            evidence=["https://reddit.com/r/wsb/123"],
        )
        assert source.source == SignalSource.REDDIT
        assert source.weighted_score == 20.0


class TestGemSignal:
    def test_total_score_computation(self):
        gem = GemSignal(
            ticker_symbol="plug",
            reddit_score=20.0,
            discord_score=10.0,
            sec_score=25.0,
            news_score=15.0,
            technical_score=20.0,
        )
        assert gem.total_score == 90.0
        assert gem.classification == GemClassification.STRONG
        assert gem.source_count == 0

    def test_classification_boundaries(self):
        gem_49 = GemSignal(ticker_symbol="X", reddit_score=12, discord_score=0, sec_score=12, news_score=12, technical_score=13)
        assert gem_49.total_score == 49.0
        assert gem_49.classification == GemClassification.DISCARD

        gem_50 = GemSignal(ticker_symbol="X", reddit_score=13, discord_score=0, sec_score=12, news_score=12, technical_score=13)
        assert gem_50.total_score == 50.0
        assert gem_50.classification == GemClassification.WATCHLIST

        gem_65 = GemSignal(ticker_symbol="X", reddit_score=20, discord_score=0, sec_score=15, news_score=15, technical_score=15)
        assert gem_65.total_score == 65.0
        assert gem_65.classification == GemClassification.POTENTIAL

        gem_80 = GemSignal(ticker_symbol="X", reddit_score=20, discord_score=0, sec_score=25, news_score=20, technical_score=15)
        assert gem_80.total_score == 80.0
        assert gem_80.classification == GemClassification.STRONG

    def test_max_score_enforced(self):
        with pytest.raises(ValidationError):
            GemSignal(ticker_symbol="X", reddit_score=30.0)

        with pytest.raises(ValidationError):
            GemSignal(ticker_symbol="X", discord_score=30.0)


class TestValidationResult:
    def test_valid_pass(self):
        result = ValidationResult(
            ticker_symbol="aapl",
            is_valid=True,
            checks={"active": True, "cross_ref": True},
            source_count=3,
        )
        assert result.ticker_symbol == "AAPL"
        assert result.is_valid is True

    def test_valid_fail(self):
        result = ValidationResult(
            ticker_symbol="xyz",
            is_valid=False,
            checks={"active": False},
            failures=["Ticker not actively trading"],
            source_count=1,
        )
        assert result.is_valid is False
        assert len(result.failures) == 1
