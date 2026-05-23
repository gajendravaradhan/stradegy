from typing import Any

from loguru import logger

from stradegy.engine.research.models import (
    EarningsSignal,
    GemClassification,
    GemSignal,
    InsiderSignal,
    SECFiling,
    SignalSource,
    SourceScore,
    TechnicalScore,
    TrendsSignal,
)


class GemDetector:
    def __init__(self):
        self.weights = {
            SignalSource.REDDIT: 20.0,
            SignalSource.DISCORD: 20.0,
            SignalSource.STOCKTWITS: 15.0,
            SignalSource.INSIDER: 15.0,
            SignalSource.TRENDS: 10.0,
            SignalSource.EARNINGS: 10.0,
            SignalSource.SEC: 20.0,
            SignalSource.NEWS: 15.0,
            SignalSource.TECHNICAL: 20.0,
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

    def score_stocktwits(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.STOCKTWITS,
                raw_score=0.0,
                weight=self.weights[SignalSource.STOCKTWITS],
                weighted_score=0.0,
            )
        avg_sentiment = sum(m.get("sentiment_compound", 0) for m in mentions) / len(mentions)
        avg_likes = sum(m.get("likes", 0) for m in mentions) / len(mentions)
        avg_reshares = sum(m.get("reshares", 0) for m in mentions) / len(mentions)
        watchlist = max(m.get("watchlist_count", 0) for m in mentions)
        engagement = min((avg_likes + avg_reshares * 2) / 20.0 * 10.0, 10.0)
        sentiment = min(max(avg_sentiment, 0) / 0.6 * 5.0, 5.0)
        trending = min(watchlist / 5000.0 * 5.0, 5.0)
        raw_score = engagement + sentiment + trending
        return SourceScore(
            source=SignalSource.STOCKTWITS,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.STOCKTWITS],
            weighted_score=round(raw_score, 2),
            evidence=[m.get("message_url", "") for m in mentions[:3]],
        )

    def score_insider(self, signals: list[InsiderSignal]) -> SourceScore:
        if not signals:
            return SourceScore(
                source=SignalSource.INSIDER,
                raw_score=0.0,
                weight=self.weights[SignalSource.INSIDER],
                weighted_score=0.0,
            )
        purchases = [s for s in signals if s.transaction_type in ("P - Purchase", "P")]
        cluster = any(s.is_cluster for s in purchases)
        total_value = sum(s.total_value for s in purchases)
        score = 0.0
        if cluster:
            score += 10.0
        elif len(purchases) >= 1:
            score += 5.0
        if total_value > 100000:
            score += 5.0
        evidence = [s.filing_url for s in purchases[:3] if s.filing_url]
        return SourceScore(
            source=SignalSource.INSIDER,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.INSIDER],
            weighted_score=round(score, 2),
            evidence=evidence,
        )

    def score_trends(self, trend: TrendsSignal | None) -> SourceScore:
        if not trend or trend.interest_score <= 0:
            return SourceScore(
                source=SignalSource.TRENDS,
                raw_score=0.0,
                weight=self.weights[SignalSource.TRENDS],
                weighted_score=0.0,
            )
        score = min(trend.interest_score / 100.0 * 7.0, 7.0)
        if trend.direction == "up" and trend.interest_vs_90d_avg > 0.3:
            score += 3.0
        elif trend.direction == "up":
            score += 1.5
        return SourceScore(
            source=SignalSource.TRENDS,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.TRENDS],
            weighted_score=round(score, 2),
        )

    def score_earnings(self, earnings: list[EarningsSignal]) -> SourceScore:
        if not earnings:
            return SourceScore(
                source=SignalSource.EARNINGS,
                raw_score=0.0,
                weight=self.weights[SignalSource.EARNINGS],
                weighted_score=0.0,
            )
        upcoming = [e for e in earnings if e.is_upcoming and e.days_until <= 7]
        past_surprises = [e for e in earnings if e.surprise_pct is not None and e.surprise_pct > 20]
        score = 0.0
        if upcoming:
            score += 3.0
        if past_surprises:
            score += min(len(past_surprises) * 3.5, 7.0)
        return SourceScore(
            source=SignalSource.EARNINGS,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.EARNINGS],
            weighted_score=round(score, 2),
        )

    def detect(
        self,
        ticker: str,
        reddit_mentions: list[dict[str, Any]] | None = None,
        discord_mentions: list[dict[str, Any]] | None = None,
        stocktwits_mentions: list[dict[str, Any]] | None = None,
        insider_signals: list[InsiderSignal] | None = None,
        trends: TrendsSignal | None = None,
        earnings: list[EarningsSignal] | None = None,
        sec_filing: SECFiling | None = None,
        news_sentiment: dict[str, Any] | None = None,
        technical: TechnicalScore | None = None,
    ) -> GemSignal:
        reddit_score = self.score_reddit(reddit_mentions or [])
        discord_score = self.score_discord(discord_mentions or [])
        stocktwits_score = self.score_stocktwits(stocktwits_mentions or [])
        insider_score = self.score_insider(insider_signals or [])
        trends_score = self.score_trends(trends)
        earnings_score = self.score_earnings(earnings or [])
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

        sources = [s for s in [
            reddit_score, discord_score, stocktwits_score, insider_score,
            trends_score, earnings_score, sec_score, news_score, tech_score,
        ] if s.raw_score > 0]
        evidence = []
        for s in sources:
            evidence.extend(s.evidence)

        gem = GemSignal(
            ticker_symbol=ticker,
            reddit_score=reddit_score.weighted_score,
            discord_score=discord_score.weighted_score,
            stocktwits_score=stocktwits_score.weighted_score,
            insider_score=insider_score.weighted_score,
            trends_score=trends_score.weighted_score,
            earnings_score=earnings_score.weighted_score,
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
