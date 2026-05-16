import pytest

from stradegy.engine.research.gem_detector import GemDetector
from stradegy.engine.research.models import (
    GemClassification,
    GemSignal,
    SECFiling,
    SignalSource,
    TechnicalScore,
)
from stradegy.engine.research.validator import Validator


class TestGemDetector:
    def test_no_signals(self):
        detector = GemDetector()
        gem = detector.detect("FAKE")
        assert gem.total_score == 0.0
        assert gem.classification == GemClassification.DISCARD

    def test_reddit_only_not_enough(self):
        detector = GemDetector()
        mentions = [
            {"sentiment_compound": 0.8, "velocity_vs_avg": 4.0, "upvote_ratio": 0.9, "post_url": "https://reddit.com/r/wsb/1"},
        ]
        gem = detector.detect("FAKE", reddit_mentions=mentions)
        assert gem.source_count == 1
        assert gem.reddit_score > 0
        assert gem.total_score < 50

    def test_multi_source_strong_gem(self):
        detector = GemDetector()
        mentions = [
            {"sentiment_compound": 0.9, "velocity_vs_avg": 5.0, "upvote_ratio": 0.95, "post_url": "https://reddit.com/r/wsb/1"},
        ]
        filing = SECFiling(
            ticker_symbol="FAKE",
            filing_type="10-K",
            filing_date="2024-01-01",
            filing_url="https://sec.gov/...",
            revenue_growth_yoy=0.30,
            insider_net_buys=3,
            cash_to_debt_ratio=2.5,
        )
        news = {"compound": 0.8, "positive_ratio": 0.8, "sample_size": 10}
        tech = TechnicalScore(
            ticker_symbol="FAKE",
            price=50.0,
            price_vs_sma15=1.05,
            price_vs_20day_high=0.98,
            volume_vs_50day_avg=2.0,
            rsi_14=45,
            passes_price_filter=True,
            passes_volume_filter=True,
            passes_market_cap_filter=True,
            passes_rsi_filter=True,
            overall_pass=True,
        )
        gem = detector.detect(
            "FAKE",
            reddit_mentions=mentions,
            sec_filing=filing,
            news_sentiment=news,
            technical=tech,
        )
        assert gem.source_count >= 2
        assert gem.total_score >= 50

    def test_max_score(self):
        detector = GemDetector()
        mentions = [
            {"sentiment_compound": 1.0, "velocity_vs_avg": 10.0, "upvote_ratio": 1.0, "post_url": "https://reddit.com/r/wsb/1"},
        ] * 10
        filing = SECFiling(
            ticker_symbol="FAKE",
            filing_type="10-K",
            filing_date="2024-01-01",
            filing_url="https://sec.gov/...",
            revenue_growth_yoy=0.50,
            insider_net_buys=10,
            cash_to_debt_ratio=10.0,
        )
        news = {"compound": 1.0, "positive_ratio": 1.0, "sample_size": 20}
        tech = TechnicalScore(
            ticker_symbol="FAKE",
            price=50.0,
            price_vs_sma15=1.2,
            price_vs_20day_high=1.05,
            volume_vs_50day_avg=5.0,
            rsi_14=30,
            passes_price_filter=True,
            passes_volume_filter=True,
            passes_market_cap_filter=True,
            passes_rsi_filter=True,
            overall_pass=True,
        )
        gem = detector.detect(
            "FAKE",
            reddit_mentions=mentions,
            sec_filing=filing,
            news_sentiment=news,
            technical=tech,
        )
        assert gem.total_score <= 100.0
        assert gem.total_score >= 80.0


class TestValidator:
    def test_valid_gem(self):
        validator = Validator()
        gem = GemSignal(
            ticker_symbol="AAPL",
            reddit_score=20.0,
            sec_score=25.0,
            news_score=15.0,
            technical_score=20.0,
            source_count=4,
            evidence_urls=["https://example.com"],
        )
        result = validator.validate(gem)
        assert result.is_valid is True
        assert result.checks["cross_reference"] is True
        assert result.checks["evidence"] is True

    def test_single_source_fails(self):
        validator = Validator()
        gem = GemSignal(
            ticker_symbol="XYZ",
            reddit_score=20.0,
            source_count=1,
            evidence_urls=["https://example.com"],
        )
        result = validator.validate(gem)
        assert result.is_valid is False
        assert result.checks["cross_reference"] is False
        assert "Less than 2 independent signal sources" in result.failures

    def test_no_evidence_fails(self):
        validator = Validator()
        gem = GemSignal(
            ticker_symbol="ABC",
            reddit_score=20.0,
            sec_score=25.0,
            source_count=2,
            evidence_urls=[],
        )
        result = validator.validate(gem)
        assert result.is_valid is False
        assert result.checks["evidence"] is False
