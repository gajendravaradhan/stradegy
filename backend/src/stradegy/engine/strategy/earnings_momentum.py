import pandas as pd

from stradegy.engine.strategy.base import BaseStrategy, Signal
from stradegy.engine.strategy.indicators import TechnicalIndicators


class EarningsMomentumStrategy(BaseStrategy):
    def __init__(self, macd_threshold: float = 0.0, volume_mult: float = 1.2):
        super().__init__("EarningsMomentum")
        self.macd_threshold = macd_threshold
        self.volume_mult = volume_mult

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        df = df.copy()
        macd_df = TechnicalIndicators.macd(df["close"])
        if macd_df is not None:
            df["macd"] = macd_df["MACD_12_26_9"]
            df["macd_signal"] = macd_df["MACDs_12_26_9"]
            df["macd_hist"] = macd_df["MACDh_12_26_9"]
        df["rsi"] = TechnicalIndicators.rsi(df["close"])
        df["volume_sma_20"] = df["volume"].rolling(20).mean()

        signals = []
        for i in range(50, len(df)):
            row = df.iloc[i]
            if pd.isna(row.get("macd")):
                continue

            macd_cross_up = (
                row["macd"] > row["macd_signal"] and
                df.iloc[i-1]["macd"] <= df.iloc[i-1]["macd_signal"]
            )
            macd_cross_down = (
                row["macd"] < row["macd_signal"] and
                df.iloc[i-1]["macd"] >= df.iloc[i-1]["macd_signal"]
            )
            volume_confirmed = row["volume"] > row["volume_sma_20"] * self.volume_mult
            rsi_ok = 40 < row["rsi"] < 70

            if macd_cross_up and volume_confirmed and rsi_ok:
                signals.append(self._create_signal(
                    ticker, df.index[i], "buy", row["close"],
                    confidence=min(abs(row["macd_hist"]) / row["close"] * 100, 1.0),
                    metadata={"macd": row["macd"], "macd_signal": row["macd_signal"]},
                ))
            elif macd_cross_down and volume_confirmed:
                signals.append(self._create_signal(
                    ticker, df.index[i], "sell", row["close"],
                    confidence=min(abs(row["macd_hist"]) / row["close"] * 100, 1.0),
                    metadata={"macd": row["macd"], "macd_signal": row["macd_signal"]},
                ))

        return signals
