import pytest

from stradegy.engine.research.sentiment import FinBertPipeline, VaderSingleton


class TestVaderSingleton:
    def test_singleton_behavior(self):
        a = VaderSingleton()
        b = VaderSingleton()
        assert a is b

    def test_positive_sentiment(self):
        analyzer = VaderSingleton()
        result = analyzer.analyze("Apple stock is going to the moon! Great earnings beat!")
        assert result["compound"] > 0.05
        assert result["label"] == "positive"

    def test_negative_sentiment(self):
        analyzer = VaderSingleton()
        result = analyzer.analyze("Terrible results, stock crashing, sell everything")
        assert result["compound"] < -0.05
        assert result["label"] == "negative"

    def test_neutral_sentiment(self):
        analyzer = VaderSingleton()
        result = analyzer.analyze("The stock traded at $150 today.")
        assert result["label"] == "neutral"

    def test_empty_text(self):
        analyzer = VaderSingleton()
        result = analyzer.analyze("")
        assert result["compound"] == 0.0
        assert result["label"] == "neutral"

    def test_batch_analyze(self):
        analyzer = VaderSingleton()
        texts = ["Great news!", "Bad news.", "The stock closed at $150."]
        results = analyzer.batch_analyze(texts)
        assert len(results) == 3
        assert results[0]["label"] == "positive"
        assert results[1]["label"] == "negative"
        assert results[2]["label"] == "neutral"

    def test_aggregate(self):
        analyzer = VaderSingleton()
        texts = ["Amazing!", "Good!", "Okay.", "Bad.", "Terrible!"]
        agg = analyzer.aggregate(texts)
        assert "compound" in agg
        assert "mean" in agg
        assert agg["sample_size"] == 5

    def test_aggregate_empty(self):
        analyzer = VaderSingleton()
        agg = analyzer.aggregate([])
        assert agg["compound"] == 0.0
        assert agg["sample_size"] == 0


class TestFinBertPipeline:
    @pytest.fixture(scope="class")
    def finbert(self):
        return FinBertPipeline(device="cpu")

    def test_analyze_positive(self, finbert):
        result = finbert.analyze("The company reported record profits and strong guidance")
        assert result["label"] in ["positive", "neutral"]
        assert "compound" in result

    def test_analyze_negative(self, finbert):
        result = finbert.analyze("Bankruptcy filing and massive layoffs announced")
        assert result["label"] in ["negative", "neutral"]

    def test_analyze_empty(self, finbert):
        result = finbert.analyze("")
        assert result["label"] == "neutral"

    def test_batch_analyze(self, finbert):
        texts = [
            "Strong quarterly earnings beat expectations",
            "Revenue declined significantly year over year",
            "The stock price remained unchanged",
        ]
        results = finbert.batch_analyze(texts, batch_size=8)
        assert len(results) == 3
        labels = [r["label"] for r in results]
        assert "positive" in labels or "negative" in labels or "neutral" in labels

    def test_batch_analyze_empty(self, finbert):
        results = finbert.batch_analyze([])
        assert len(results) == 0

    def test_aggregate(self, finbert):
        texts = [
            "Outstanding performance and growth",
            "Disappointing results missed targets",
            "Results were in line with expectations",
        ]
        agg = finbert.aggregate(texts)
        assert "compound" in agg
        assert "positive_ratio" in agg
        assert "negative_ratio" in agg
        assert agg["sample_size"] == 3

    def test_aggregate_empty(self, finbert):
        agg = finbert.aggregate([])
        assert agg["compound"] == 0.0
        assert agg["sample_size"] == 0
