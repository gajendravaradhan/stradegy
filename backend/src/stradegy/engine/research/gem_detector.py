from typing import Any

from loguru import logger

from stradegy.engine.research.models import (
    AdanosSentimentScore,
    EarningsSignal,
    ExtendedHoursQuote,
    FearGreedSignal,
    FINRAShortInterest,
    FMPGradeChange,
    FredIndicator,
    GemSignal,
    InsiderSignal,
    KeyVexSignal,
    OptionsSignal,
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
            SignalSource.ALPACA_NEWS: 15.0,
            SignalSource.HACKERNEWS: 10.0,
            SignalSource.TELEGRAM: 15.0,
            SignalSource.BLUESKY: 15.0,
            SignalSource.YOUTUBE: 10.0,
            SignalSource.FRED: 10.0,
            SignalSource.FEAR_GREED: 8.0,
            SignalSource.OPTIONS: 15.0,
            SignalSource.TWELVE_DATA: 10.0,
            SignalSource.FMP: 12.0,
            SignalSource.FINRA: 12.0,
            SignalSource.KEYVEX: 15.0,
            SignalSource.ADANOS: 10.0,
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

    def score_alpaca_news(self, articles: list[dict[str, Any]]) -> SourceScore:
        if not articles:
            return SourceScore(
                source=SignalSource.ALPACA_NEWS,
                raw_score=0.0,
                weight=self.weights[SignalSource.ALPACA_NEWS],
                weighted_score=0.0,
            )
        avg_sentiment = sum(a.get("sentiment_compound", 0) for a in articles) / len(articles)
        count_score = min(len(articles) / 5.0 * 5.0, 5.0)
        sentiment_score = min(max(avg_sentiment, 0) / 0.6 * 10.0, 10.0)
        raw_score = count_score + sentiment_score
        return SourceScore(
            source=SignalSource.ALPACA_NEWS,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.ALPACA_NEWS],
            weighted_score=round(raw_score, 2),
            evidence=[a.get("article_url", "") for a in articles[:3]],
        )

    def score_hackernews(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.HACKERNEWS,
                raw_score=0.0,
                weight=self.weights[SignalSource.HACKERNEWS],
                weighted_score=0.0,
            )
        avg_points = sum(m.get("points", 0) for m in mentions) / len(mentions)
        avg_comments = sum(m.get("num_comments", 0) for m in mentions) / len(mentions)
        engagement = min((avg_points + avg_comments * 2) / 50.0 * 8.0, 8.0)
        count_bonus = min(len(mentions) / 5.0 * 2.0, 2.0)
        raw_score = engagement + count_bonus
        return SourceScore(
            source=SignalSource.HACKERNEWS,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.HACKERNEWS],
            weighted_score=round(raw_score, 2),
            evidence=[m.get("story_url", "") for m in mentions[:3]],
        )

    def score_telegram(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.TELEGRAM,
                raw_score=0.0,
                weight=self.weights[SignalSource.TELEGRAM],
                weighted_score=0.0,
            )
        avg_sentiment = sum(m.get("sentiment_compound", 0) for m in mentions) / len(mentions)
        avg_views = sum(m.get("views", 0) for m in mentions) / len(mentions)
        avg_reactions = sum(m.get("reactions", 0) for m in mentions) / len(mentions)
        engagement = min((avg_views * 0.01 + avg_reactions * 2) / 10.0 * 10.0, 10.0)
        sentiment_score = min(max(avg_sentiment, 0) / 0.6 * 5.0, 5.0)
        raw_score = engagement + sentiment_score
        return SourceScore(
            source=SignalSource.TELEGRAM,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.TELEGRAM],
            weighted_score=round(raw_score, 2),
            evidence=[
                f"tg://{m.get('channel_name', '')}/{m.get('message_id', '')}"
                for m in mentions[:3]
            ],
        )

    def score_bluesky(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.BLUESKY,
                raw_score=0.0,
                weight=self.weights[SignalSource.BLUESKY],
                weighted_score=0.0,
            )
        avg_likes = sum(m.get("likes", 0) for m in mentions) / len(mentions)
        avg_reposts = sum(m.get("reposts", 0) for m in mentions) / len(mentions)
        avg_replies = sum(m.get("replies", 0) for m in mentions) / len(mentions)
        avg_sentiment = sum(m.get("sentiment_compound", 0) for m in mentions) / len(mentions)
        engagement = min((avg_likes + avg_reposts * 2 + avg_replies) / 20.0 * 10.0, 10.0)
        sentiment_score = min(max(avg_sentiment, 0) / 0.6 * 5.0, 5.0)
        raw_score = engagement + sentiment_score
        return SourceScore(
            source=SignalSource.BLUESKY,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.BLUESKY],
            weighted_score=round(raw_score, 2),
            evidence=[m.get("post_url", "") for m in mentions[:3]],
        )

    def score_youtube(self, mentions: list[dict[str, Any]]) -> SourceScore:
        if not mentions:
            return SourceScore(
                source=SignalSource.YOUTUBE,
                raw_score=0.0,
                weight=self.weights[SignalSource.YOUTUBE],
                weighted_score=0.0,
            )
        avg_likes = sum(m.get("likes", 0) for m in mentions) / len(mentions)
        positive_count = sum(1 for m in mentions if m.get("sentiment_label") == "positive")
        sentiment_ratio = positive_count / max(len(mentions), 1)
        engagement = min(avg_likes / 10.0 * 5.0, 5.0)
        sentiment_score = sentiment_ratio * 5.0
        raw_score = engagement + sentiment_score
        return SourceScore(
            source=SignalSource.YOUTUBE,
            raw_score=round(raw_score, 2),
            weight=self.weights[SignalSource.YOUTUBE],
            weighted_score=round(raw_score, 2),
            evidence=[m.get("video_url", "") for m in mentions[:3]],
        )

    def score_fred(self, indicators: list[FredIndicator] | None) -> SourceScore:
        if not indicators:
            return SourceScore(
                source=SignalSource.FRED,
                raw_score=0.0,
                weight=self.weights[SignalSource.FRED],
                weighted_score=0.0,
            )
        score = 5.0
        dxy = next((i.value for i in indicators if i.series_id == "DTWEXBGS"), None)
        treasury = next((i.value for i in indicators if i.series_id == "DGS10"), None)
        gdp = next((i.value for i in indicators if i.series_id == "GDP"), None)
        if dxy and dxy < 100:
            score += 3.0
        if treasury and treasury < 4.5:
            score += 2.0
        if gdp and gdp > 28000:
            score += 2.0
        return SourceScore(
            source=SignalSource.FRED,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.FRED],
            weighted_score=round(score, 2),
        )

    def score_fear_greed(self, signals: list[FearGreedSignal] | None) -> SourceScore:
        if not signals:
            return SourceScore(
                source=SignalSource.FEAR_GREED,
                raw_score=0.0,
                weight=self.weights[SignalSource.FEAR_GREED],
                weighted_score=0.0,
            )
        fg = signals[0]
        if fg.score <= 25:
            score = 8.0
        elif fg.score <= 45:
            score = 3.0
        elif fg.score <= 55:
            score = 4.0
        elif fg.score <= 75:
            score = 6.0
        else:
            score = 3.0
        return SourceScore(
            source=SignalSource.FEAR_GREED,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.FEAR_GREED],
            weighted_score=round(score, 2),
        )

    def score_options(self, signals: list[OptionsSignal] | None) -> SourceScore:
        if not signals:
            return SourceScore(
                source=SignalSource.OPTIONS,
                raw_score=0.0,
                weight=self.weights[SignalSource.OPTIONS],
                weighted_score=0.0,
            )
        total_premium = sum(s.premium for s in signals)
        max_vol_oi = max(s.vol_oi_ratio for s in signals) if signals else 0
        call_count = sum(1 for s in signals if s.option_type == "CALL")
        call_ratio = call_count / max(len(signals), 1)
        premium_score = min(total_premium / 500000.0 * 10.0, 10.0)
        vol_oi_score = min(max_vol_oi / 10.0 * 5.0, 5.0)
        raw_score = premium_score + vol_oi_score
        if call_ratio > 0.7:
            raw_score *= 1.2
        return SourceScore(
            source=SignalSource.OPTIONS,
            raw_score=round(min(raw_score, 15.0), 2),
            weight=self.weights[SignalSource.OPTIONS],
            weighted_score=round(min(raw_score, 15.0), 2),
            evidence=[f"options:{s.ticker_symbol}:{s.strike}" for s in signals[:3]],
        )

    def score_twelve_data(self, quotes: list[ExtendedHoursQuote] | None) -> SourceScore:
        if not quotes:
            return SourceScore(
                source=SignalSource.TWELVE_DATA,
                raw_score=0.0,
                weight=self.weights[SignalSource.TWELVE_DATA],
                weighted_score=0.0,
            )
        q = quotes[0]
        score = 3.0
        if q.market_state == "pre":
            if q.pre_market_change_pct and q.pre_market_change_pct > 2.0:
                score += 5.0
            elif q.pre_market_change_pct and q.pre_market_change_pct > 0:
                score += 2.0
        elif q.market_state == "post":
            if q.post_market_change_pct and q.post_market_change_pct > 1.5:
                score += 5.0
            elif q.post_market_change_pct and q.post_market_change_pct > 0:
                score += 2.0
        if q.pre_market_change_pct or q.post_market_change_pct:
            score += 2.0
        return SourceScore(
            source=SignalSource.TWELVE_DATA,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.TWELVE_DATA],
            weighted_score=round(score, 2),
        )

    def score_fmp(self, grades: list[FMPGradeChange] | None) -> SourceScore:
        if not grades:
            return SourceScore(
                source=SignalSource.FMP,
                raw_score=0.0,
                weight=self.weights[SignalSource.FMP],
                weighted_score=0.0,
            )
        upgrades = [g for g in grades if g.action and "upgrade" in g.action.lower()]
        downgrades = [g for g in grades if g.action and "downgrade" in g.action.lower()]
        price_target_up = [
            g for g in grades
            if g.price_target and g.previous_price_target
            and g.price_target > g.previous_price_target
        ]
        score = len(upgrades) * 3.5 + len(price_target_up) * 2.0 - len(downgrades) * 2.0
        score = max(0.0, min(score, 12.0))
        return SourceScore(
            source=SignalSource.FMP,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.FMP],
            weighted_score=round(score, 2),
        )

    def score_finra(self, si_data: list[FINRAShortInterest] | None) -> SourceScore:
        if not si_data:
            return SourceScore(
                source=SignalSource.FINRA,
                raw_score=0.0,
                weight=self.weights[SignalSource.FINRA],
                weighted_score=0.0,
            )
        si = si_data[0]
        score = 6.0
        if si.days_to_cover and si.days_to_cover > 10:
            score -= 3.0
        elif si.days_to_cover and si.days_to_cover < 3:
            score += 2.0
        if si.short_interest_ratio and si.short_interest_ratio > 20:
            score -= 2.0
        elif si.short_interest_ratio and si.short_interest_ratio < 5:
            score += 2.0
        return SourceScore(
            source=SignalSource.FINRA,
            raw_score=round(max(0.0, score), 2),
            weight=self.weights[SignalSource.FINRA],
            weighted_score=round(max(0.0, score), 2),
        )

    def score_keyvex(self, signals: list[KeyVexSignal] | None) -> SourceScore:
        if not signals:
            return SourceScore(
                source=SignalSource.KEYVEX,
                raw_score=0.0,
                weight=self.weights[SignalSource.KEYVEX],
                weighted_score=0.0,
            )
        kv = signals[0]
        score = 5.0
        if kv.dark_pool_volume and kv.dark_pool_volume > 100000:
            score += 5.0
        if kv.congressional_trade_type and "P" in str(kv.congressional_trade_type).upper():
            score += 5.0
        if kv.insider_transaction_type and "P" in str(kv.insider_transaction_type).upper():
            score += 5.0
        if kv.institution_holdings_change_pct and kv.institution_holdings_change_pct > 5:
            score += 3.0
        if kv.sec_fails_to_deliver and kv.sec_fails_to_deliver > 100000:
            score -= 5.0
        score = max(0.0, min(score, 20.0))
        return SourceScore(
            source=SignalSource.KEYVEX,
            raw_score=round(score, 2),
            weight=self.weights[SignalSource.KEYVEX],
            weighted_score=round(score, 2),
        )

    def score_adanos(self, sentiments: list[AdanosSentimentScore] | None) -> SourceScore:
        if not sentiments:
            return SourceScore(
                source=SignalSource.ADANOS,
                raw_score=0.0,
                weight=self.weights[SignalSource.ADANOS],
                weighted_score=0.0,
            )
        as_ = sentiments[0]
        score = 0.0
        score += min(max(as_.aggregated_score, 0) / 0.6 * 5.0, 5.0)
        score += as_.aggregated_confidence * 3.0
        if as_.reddit_mentions > 10:
            score += 2.0
        if as_.x_mentions > 5:
            score += 2.0
        return SourceScore(
            source=SignalSource.ADANOS,
            raw_score=round(min(score, 10.0), 2),
            weight=self.weights[SignalSource.ADANOS],
            weighted_score=round(min(score, 10.0), 2),
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
        alpaca_news_mentions: list[dict[str, Any]] | None = None,
        hackernews_mentions: list[dict[str, Any]] | None = None,
        telegram_mentions: list[dict[str, Any]] | None = None,
        bluesky_mentions: list[dict[str, Any]] | None = None,
        youtube_mentions: list[dict[str, Any]] | None = None,
        fred_indicators: list[FredIndicator] | None = None,
        fear_greed_signals: list[FearGreedSignal] | None = None,
        options_signals: list[OptionsSignal] | None = None,
        twelve_data_quotes: list[ExtendedHoursQuote] | None = None,
        fmp_grades: list[FMPGradeChange] | None = None,
        finra_si: list[FINRAShortInterest] | None = None,
        keyvex_signals: list[KeyVexSignal] | None = None,
        adanos_sentiments: list[AdanosSentimentScore] | None = None,
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

        alpaca_news_score = self.score_alpaca_news(alpaca_news_mentions or [])
        hackernews_score = self.score_hackernews(hackernews_mentions or [])
        telegram_score = self.score_telegram(telegram_mentions or [])
        bluesky_score = self.score_bluesky(bluesky_mentions or [])
        youtube_score = self.score_youtube(youtube_mentions or [])
        fred_score = self.score_fred(fred_indicators)
        fear_greed_score = self.score_fear_greed(fear_greed_signals)
        options_score = self.score_options(options_signals)
        twelve_data_score = self.score_twelve_data(twelve_data_quotes)
        fmp_score = self.score_fmp(fmp_grades)
        finra_score = self.score_finra(finra_si)
        keyvex_score = self.score_keyvex(keyvex_signals)
        adanos_score = self.score_adanos(adanos_sentiments)

        sources = [s for s in [
            reddit_score, discord_score, stocktwits_score, insider_score,
            trends_score, earnings_score, sec_score, news_score, tech_score,
            alpaca_news_score, hackernews_score, telegram_score, bluesky_score,
            youtube_score, fred_score, fear_greed_score, options_score,
            twelve_data_score, fmp_score, finra_score, keyvex_score, adanos_score,
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
            alpaca_news_score=alpaca_news_score.weighted_score,
            hackernews_score=hackernews_score.weighted_score,
            telegram_score=telegram_score.weighted_score,
            bluesky_score=bluesky_score.weighted_score,
            youtube_score=youtube_score.weighted_score,
            fred_score=fred_score.weighted_score,
            fear_greed_score=fear_greed_score.weighted_score,
            options_score=options_score.weighted_score,
            twelve_data_score=twelve_data_score.weighted_score,
            fmp_score=fmp_score.weighted_score,
            finra_score=finra_score.weighted_score,
            keyvex_score=keyvex_score.weighted_score,
            adanos_score=adanos_score.weighted_score,
            source_count=len(sources),
            sources=sources,
            evidence_urls=evidence[:5],
        )

        logger.info(
            f"Gem detection for {ticker}: score={gem.total_score}, "
            f"class={gem.classification.value}, sources={gem.source_count}"
        )
        return gem
