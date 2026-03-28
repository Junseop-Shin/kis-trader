import pandas as pd
import pandas_ta as ta
from .base import BaseAlgorithm


class StochasticAlgorithm(BaseAlgorithm):
    """Stochastic oscillator (%K/%D crossover) strategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        k_period = self.params.get("k_period", 14)
        d_period = self.params.get("d_period", 3)
        oversold = self.params.get("oversold", 20)
        overbought = self.params.get("overbought", 80)

        stoch = ta.stoch(df["high"], df["low"], df["close"], k=k_period, d=d_period)
        if stoch is None:
            return pd.Series(0, index=df.index)

        k_line = stoch.iloc[:, 0]
        d_line = stoch.iloc[:, 1]

        prev_k = k_line.shift(1)
        prev_d = d_line.shift(1)

        signals = pd.Series(0, index=df.index)

        # Buy: %K crosses above %D in oversold zone
        signals[
            (prev_k <= prev_d) & (k_line > d_line) & (k_line < oversold)
        ] = 1
        # Sell: %K crosses below %D in overbought zone
        signals[
            (prev_k >= prev_d) & (k_line < d_line) & (k_line > overbought)
        ] = -1

        return signals
