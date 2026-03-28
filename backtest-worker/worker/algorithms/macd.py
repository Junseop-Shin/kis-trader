import pandas as pd
import pandas_ta as ta
from .base import BaseAlgorithm


class MACDAlgorithm(BaseAlgorithm):
    """MACD signal line crossover strategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params.get("fast", 12)
        slow = self.params.get("slow", 26)
        signal_period = self.params.get("signal", 9)

        macd_df = ta.macd(df["close"], fast=fast, slow=slow, signal=signal_period)
        if macd_df is None:
            return pd.Series(0, index=df.index)

        macd_line = macd_df.iloc[:, 0]
        signal_line = macd_df.iloc[:, 2]

        prev_macd = macd_line.shift(1)
        prev_signal = signal_line.shift(1)

        signals = pd.Series(0, index=df.index)

        # Buy when MACD crosses above signal line
        signals[(prev_macd <= prev_signal) & (macd_line > signal_line)] = 1
        # Sell when MACD crosses below signal line
        signals[(prev_macd >= prev_signal) & (macd_line < signal_line)] = -1

        return signals
