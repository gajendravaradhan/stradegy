from typing import Any

from loguru import logger

from stradegy.engine.research.models import (
    GemClassification,
    GemSignal,
    SECFiling,
    SignalSource,
    SourceScore,
    TechnicalScore,
)


class GemDetector:
    def __init__(self):
        self.weights = {
            SignalSource.REDDIT: 25.0,
            SignalSource.DISCORD: 25.0,
            SignalSource.SEC: 30.0,
            SignalSource.NEWS: 20.0,
            SignalSource.TECHNICAL: 25.0,
        }

    def score_reddit(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.REDDIT,
                raw_score=0.0,
                weight=self.weights[SignalSource.REDDIT],
                weighted_score=0.0,
            )

        avg_sentiment = sum(m["sentiment_compound"] for m in mentions) / len(mentions)
        avg_velocity = sum(m.get("velocity_vs_avg", 0) for m in mentions) / len(mentions)
        avg_upvote = sum(m.get("upvote_ratio", 0) for m in mentions) / len(mentions)

        velocity_score = min(avg_velocity / 3.0 * 15.0, 15.0)
        sentiment_score = min(max(avg_sentiment, 0) / 0.6 * 10.0, 10.0)
        raw_score = velocity_score + sentiment_score

        return SourceScore(
            source=SignalSource.REDDIT,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.REDDIT],
            weighted_score=round(raw_score, 2),
            evidence=[m["post_url"] for m in mentions[:3]],
        )

    def score_discord(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.DISCORD,
                raw_score=0.0,
                weight=self.weights[SignalSource.DISCORD],
                weighted_score=0.0,
            )

        avg_sentiment = sum(m["sentiment_compound"] for m in mentions) / len(mentions)
        avg_reactions = sum(m.get("num_reactions", 0) for m in mentions) / len(mentions)
        avg_replies = sum(m.get("reply_count", 0) for m in mentions) / len(mentions)

        engagement_score = min((avg_reactions + avg_replies * 2) / 10.0 * 15.0, 15.0)
        sentiment_score = min(max(avg_sentiment, 0) / 0.6 * 10.0, 10.0)
        raw_score = engagement_score + sentiment_score

        return SourceScore(
            source=SignalSource.DISCORD,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.DISCORD],
            weighted_score=round(raw_score, 2),
            evidence=[m["message_url"] for m in mentions[:3]],
        )

    def score_sec(self, filing: SECFiling | None) -> SourceScore:
        if not filing:
            return SourceScore(
                source=SignalSource.SEC,
                raw_score=0.0,
                weight=self.weights[SignalSource.SEC],
                weighted_score=0.0,
            )

        score = 0.0
        if filing.revenue_growth_yoy and filing.revenue_growth_yoy > 0.20:
            score += 15.0
        elif filing.revenue_growth_yoy and filing.revenue_growth_yoy > 0.10:
            score += 8.0

        if filing.insider_net_buys and filing.insider_net_buys >= 2:
            score += 10.0
        elif filing.insider_net_buys and filing.insider_net_buys > 0:
            score += 5.0

        if filing.cash_to_debt_ratio and filing.cash_to_debt_ratio > 1.0:
            score += 5.0

        return SourceScore(
            source=SignalSource.SEC,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.SEC],
            weighted_score=round(score, 2),
            evidence=[filing.filing_url],
        )

    def score_news(self, sentiment: dict[str, Any]) -> SourceScore:
        compound = sentiment.get("compound", 0.0)
        positive_ratio = sentiment.get("positive_ratio", 0.0)
        sample_size = sentiment.get("sample_size", 0)

        if sample_size == 0:
            return SourceScore(
                source=SignalSource.NEWS,
                raw_score=0.0,
                weight=self.weights[SignalSource.NEWS],
                weighted_score=0.0,
            )

        score = min(max(compound, 0) / 0.7 * 20.0, 20.0)
        if positive_ratio > 0.7:
            score = max(score, 15.0)

        return SourceScore(
            source=SignalSource.NEWS,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.NEWS],
            weighted_score=round(score, 2),
            evidence=[a["url"] for a in sentiment.get("articles", [])[:3]],
        )

    def score_technical(self, tech: TechnicalScore) -> SourceScore:
        if not tech.overall_pass:
            return SourceScore(
                source=SignalSource.TECHNICAL,
                raw_score=0.0,
                weight=self.weights[SignalSource.TECHNICAL],
                weighted_score=0.0,
            )

        score = 0.0
        if tech.passes_price_filter:
            score += 8.0
        if tech.passes_volume_filter:
            score += 7.0
        if tech.passes_rsi_filter:
            score += 10.0

        return SourceScore(
            source=SignalSource.TECHNICAL,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.TECHNICAL],
            weighted_score=round(score, 2),
        )

    def detect(
        self,
        ticker: str,
        reddit_mentions: list[dict[str, Any]] | None = None,
        discord_mentions: list[dict[str, Any]] | None = None,
        sec_filing: SECFiling | None = None,
        news_sentiment: dict[str, Any] | None = None,
        technical: TechnicalScore | None = None,
    ) -> GemSignal:
        reddit_score = self.score_reddit(reddit_mentions or [])
        discord_score = self.score_discord(discord_mentions or [])
        sec_score = self.score_sec(sec_filing)
        news_score = self.score_news(news_sentiment or {})
        if technical is None:
            technical = TechnicalScore(
                ticker_symbol=ticker,
                price=1.0,
                price_vs_sma15=0.0,
                price_vs_20day_high=0.0,
                volume_vs_50day_avg=0.0,
                passes_price_filter=False,
                passes_volume_filter=False,
                passes_market_cap_filter=False,
                passes_rsi_filter=False,
                overall_pass=False,
            )
        tech_score = self.score_technical(technical)

        sources = [s for s in [reddit_score, discord_score, sec_score, news_score, tech_score] if s.raw_score > 0]
        evidence = []
        for s in sources:
            evidence.extend(s.evidence)

        gem = GemSignal(
            ticker_symbol=ticker,
            reddit_score=reddit_score.weighted_score,
            discord_score=discord_score.weighted_score,
            sec_score=sec_score.weighted_score,
            news_score=news_score.weighted_score,
            technical_score=tech_score.weighted_score,
            source_count=len(sources),
            sources=sources,
            evidence_urls=evidence[:5],
        )

        logger.info(
            f"Gem detection for {ticker}: score={gem.total_score}, "
            f"class={gem.classification.value}, sources={gem.source_count}"
        )
        return gem
