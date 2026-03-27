import pandas as pd
import pandas_ta as ta
from .base import BaseAlgorithm


class RSIAlgorithm(BaseAlgorithm):
    """RSI overbought/oversold strategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get("period", 14)
        oversold = self.params.get("oversold", 30)
        overbought = self.params.get("overbought", 70)

        rsi = ta.rsi(df["close"], length=period)
        if rsi is None:
            return pd.Series(0, index=df.index)

        prev_rsi = rsi.shift(1)
        signals = pd.Series(0, index=df.index)

        # Buy when RSI crosses above oversold level (was below, now above)
        signals[(prev_rsi < oversold) & (rsi >= oversold)] = 1
        # Sell when RSI crosses above overbought level (was below, now above)
        signals[(prev_rsi < overbought) & (rsi >= overbought)] = -1

        return signals
