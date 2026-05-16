from typing import Any

from loguru import logger
from vader_sentiment.vader_sentiment import SentimentIntensityAnalyzer


class VaderSingleton:
    _instance: "VaderSingleton | None" = None
    _analyzer: SentimentIntensityAnalyzer | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER SentimentIntensityAnalyzer initialized")
        return cls._instance

    def analyze(self, text: str) -> dict[str, Any]:
        if not text or not text.strip():
            return {
                "neg": 0.0,
                "neu": 1.0,
                "pos": 0.0,
                "compound": 0.0,
                "label": "neutral",
            }
        scores = self._analyzer.polarity_scores(text)
        label = (
            "positive" if scores["compound"] >= 0.05
            else "negative" if scores["compound"] <= -0.05
            else "neutral"
        )
        return {**scores, "label": label}

    def batch_analyze(self, texts: list[str]) -> list[dict[str, Any]]:
        return [self.analyze(t) for t in texts]

    def aggregate(self, texts: list[str]) -> dict[str, Any]:
        if not texts:
            return {"compound": 0.0, "label": "neutral", "sample_size": 0}
        results = [self.analyze(t)["compound"] for t in texts]
        avg = sum(results) / len(results)
        return {
            "compound": avg,
            "mean": avg,
            "min": min(results),
            "max": max(results),
            "label": (
                "positive" if avg >= 0.05
                else "negative" if avg <= -0.05
                else "neutral"
            ),
            "sample_size": len(texts),
        }


class FinBertPipeline:
    def __init__(self, device: str = "cpu"):
        self._pipeline: Any = None
        self._device = device

    def _ensure_loaded(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                import torch

                dev = -1
                if self._device == "cuda" and torch.cuda.is_available():
                    dev = 0

                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    device=dev,
                )
                logger.info(f"FinBERT loaded on device {dev}")
            except Exception as e:
                logger.error(f"Failed to load FinBERT: {e}")
                raise

    def analyze(self, text: str) -> dict[str, Any]:
        self._ensure_loaded()
        if not text or not text.strip():
            return {"label": "neutral", "score": 0.0}
        try:
            result = self._pipeline(text[:512], truncation=True)[0]
            label_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
            base = label_map.get(result["label"], 0.0)
            return {
                "label": result["label"],
                "score": result["score"],
                "compound": base * result["score"],
            }
        except Exception as e:
            logger.error(f"FinBERT analysis error: {e}")
            return {"label": "error", "score": 0.0, "error": str(e)}

    def batch_analyze(self, texts: list[str], batch_size: int = 8) -> list[dict[str, Any]]:
        self._ensure_loaded()
        if not texts:
            return []
        try:
            results = self._pipeline(
                [t[:512] for t in texts],
                batch_size=batch_size,
                truncation=True,
            )
            label_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
            return [
                {
                    "label": r["label"],
                    "score": r["score"],
                    "compound": label_map.get(r["label"], 0.0) * r["score"],
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"FinBERT batch analysis error: {e}")
            return [{"label": "error", "score": 0.0, "error": str(e)} for _ in texts]

    def aggregate(self, texts: list[str]) -> dict[str, Any]:
        if not texts:
            return {"compound": 0.0, "label": "neutral", "sample_size": 0}
        results = self.batch_analyze(texts)
        compounds = [r["compound"] for r in results if "error" not in r]
        if not compounds:
            return {"compound": 0.0, "label": "error", "sample_size": 0}
        avg = sum(compounds) / len(compounds)
        return {
            "compound": avg,
            "mean": avg,
            "positive_ratio": sum(1 for r in results if r.get("label") == "positive") / len(results),
            "negative_ratio": sum(1 for r in results if r.get("label") == "negative") / len(results),
            "neutral_ratio": sum(1 for r in results if r.get("label") == "neutral") / len(results),
            "label": (
                "positive" if avg > 0.05
                else "negative" if avg < -0.05
                else "neutral"
            ),
            "sample_size": len(results),
        }
