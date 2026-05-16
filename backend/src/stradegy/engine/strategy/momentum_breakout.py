import pandas as pd

from stradegy.engine.strategy.base import BaseStrategy, Signal
from stradegy.engine.strategy.indicators import TechnicalIndicators


class MomentumBreakoutStrategy(BaseStrategy):
    def __init__(self, adx_threshold: float = 25.0, volume_mult: float = 1.5):
        super().__init__("MomentumBreakout")
        self.adx_threshold = adx_threshold
        self.volume_mult = volume_mult

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        df = df.copy()
        df["adx"] = TechnicalIndicators.adx(df["high"], df["low"], df["close"])["ADX_14"]
        df["sma_20"] = TechnicalIndicators.sma(df["close"], 20)
        df["sma_50"] = TechnicalIndicators.sma(df["close"], 50)
        df["high_20"] = df["high"].rolling(20).max()
        df["low_20"] = df["low"].rolling(20).min()
        df["volume_sma_20"] = df["volume"].rolling(20).mean()

        signals = []
        for i in range(50, len(df)):
            row = df.iloc[i]
            if pd.isna(row["adx"]):
                continue

            volume_confirmed = row["volume"] > row["volume_sma_20"] * self.volume_mult
            trend_aligned = row["sma_20"] > row["sma_50"]
            strong_trend = row["adx"] > self.adx_threshold

            if row["close"] > row["high_20"] and volume_confirmed and trend_aligned and strong_trend:
                signals.append(self._create_signal(
                    ticker, df.index[i], "buy", row["close"],
                    confidence=min(row["adx"] / 50.0, 1.0),
                    metadata={"adx": row["adx"], "breakout": "20-day high"},
                ))
            elif row["close"] < row["low_20"] and trend_aligned and strong_trend:
                signals.append(self._create_signal(
                    ticker, df.index[i], "sell", row["close"],
                    confidence=min(row["adx"] / 50.0, 1.0),
                    metadata={"adx": row["adx"], "breakout": "20-day low"},
                ))

        return signals
