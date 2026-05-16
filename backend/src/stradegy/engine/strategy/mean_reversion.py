import pandas as pd

from stradegy.engine.strategy.base import BaseStrategy, Signal
from stradegy.engine.strategy.indicators import TechnicalIndicators


class MeanReversionStrategy(BaseStrategy):
    def __init__(self, rsi_period: int = 14, rsi_oversold: float = 30.0, rsi_overbought: float = 70.0):
        super().__init__("MeanReversion")
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        df = df.copy()
        df["rsi"] = TechnicalIndicators.rsi(df["close"], self.rsi_period)
        df["sma_20"] = TechnicalIndicators.sma(df["close"], 20)
        bb_df = TechnicalIndicators.bollinger(df["close"])
        df["bb_lower"] = bb_df["BBL_20_2.0_2.0"] if bb_df is not None and "BBL_20_2.0_2.0" in bb_df.columns else pd.Series(index=df.index)
        df["bb_upper"] = bb_df["BBU_20_2.0_2.0"] if bb_df is not None and "BBU_20_2.0_2.0" in bb_df.columns else pd.Series(index=df.index)

        signals = []
        for i in range(50, len(df)):
            row = df.iloc[i]
            if pd.isna(row["rsi"]):
                continue

            if row["rsi"] < self.rsi_oversold and row["close"] <= row["bb_lower"]:
                signals.append(self._create_signal(
                    ticker, df.index[i], "buy", row["close"],
                    confidence=(self.rsi_oversold - row["rsi"]) / self.rsi_oversold,
                    metadata={"rsi": row["rsi"], "bb_position": "lower"},
                ))
            elif row["rsi"] > self.rsi_overbought and row["close"] >= row["bb_upper"]:
                signals.append(self._create_signal(
                    ticker, df.index[i], "sell", row["close"],
                    confidence=(row["rsi"] - self.rsi_overbought) / (100 - self.rsi_overbought),
                    metadata={"rsi": row["rsi"], "bb_position": "upper"},
                ))

        return signals
