import numpy as np
import pandas as pd
import pandas_ta as ta


class TechnicalIndicators:
    @staticmethod
    def rsi(prices: pd.Series, length: int = 14) -> pd.Series:
        return ta.rsi(prices, length=length)

    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        return ta.macd(prices, fast=fast, slow=slow, signal=signal)

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
        return ta.atr(high=high, low=low, close=close, length=length)

    @staticmethod
    def bollinger(prices: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
        return ta.bbands(prices, length=length, std=std)

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        return ta.vwap(high=high, low=low, close=close, volume=volume)

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
        return ta.adx(high=high, low=low, close=close, length=length)

    @staticmethod
    def sma(prices: pd.Series, length: int = 20) -> pd.Series:
        return ta.sma(prices, length=length)

    @staticmethod
    def ema(prices: pd.Series, length: int = 20) -> pd.Series:
        return ta.ema(prices, length=length)

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3) -> pd.DataFrame:
        return ta.stoch(high=high, low=low, close=close, k=k, d=d)

    @staticmethod
    def add_all(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["rsi_14"] = TechnicalIndicators.rsi(df["close"])
        df["sma_20"] = TechnicalIndicators.sma(df["close"], 20)
        df["sma_50"] = TechnicalIndicators.sma(df["close"], 50)
        df["ema_12"] = TechnicalIndicators.ema(df["close"], 12)
        df["ema_26"] = TechnicalIndicators.ema(df["close"], 26)

        macd_df = TechnicalIndicators.macd(df["close"])
        if macd_df is not None:
            df["macd"] = macd_df["MACD_12_26_9"]
            df["macd_signal"] = macd_df["MACDs_12_26_9"]
            df["macd_hist"] = macd_df["MACDh_12_26_9"]

        df["atr_14"] = TechnicalIndicators.atr(df["high"], df["low"], df["close"])

        bb_df = TechnicalIndicators.bollinger(df["close"])
        if bb_df is not None:
            df["bb_upper"] = bb_df["BBU_20_2.0"]
            df["bb_middle"] = bb_df["BBM_20_2.0"]
            df["bb_lower"] = bb_df["BBL_20_2.0"]
            df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        adx_df = TechnicalIndicators.adx(df["high"], df["low"], df["close"])
        if adx_df is not None:
            df["adx"] = adx_df["ADX_14"]
            df["adx_pos"] = adx_df["DMP_14"]
            df["adx_neg"] = adx_df["DMN_14"]

        df["volume_sma_20"] = df["volume"].rolling(20).mean()
        return df
