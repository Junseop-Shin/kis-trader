import pandas as pd
from .base import BaseAlgorithm


class MACrossAlgorithm(BaseAlgorithm):
    """Moving Average crossover strategy (SMA/EMA golden/death cross)."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        ma_type = self.params.get("ma_type", "SMA")
        short = self.params.get("short_period", 5)
        long_ = self.params.get("long_period", 20)

        if ma_type == "EMA":
            short_ma = df["close"].ewm(span=short, adjust=False).mean()
            long_ma = df["close"].ewm(span=long_, adjust=False).mean()
        else:
            short_ma = df["close"].rolling(short).mean()
            long_ma = df["close"].rolling(long_).mean()

        position = pd.Series(0, index=df.index)
        position[short_ma > long_ma] = 1
        position[short_ma < long_ma] = -1

        prev = position.shift(1).fillna(0)
        result = pd.Series(0, index=df.index)
        result[(position == 1) & (prev == -1)] = 1   # BUY on golden cross
        result[(position == -1) & (prev == 1)] = -1   # SELL on death cross
        return result
