import pandas as pd
import pandas_ta as ta
from .base import BaseAlgorithm


class BollingerAlgorithm(BaseAlgorithm):
    """Bollinger Band breakout or mean-reversion strategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get("period", 20)
        std_dev = self.params.get("std_dev", 2.0)
        mode = self.params.get("mode", "reversion")  # 'breakout' or 'reversion'

        bb = ta.bbands(df["close"], length=period, std=std_dev)
        if bb is None:
            return pd.Series(0, index=df.index)

        lower = bb.iloc[:, 0]
        mid = bb.iloc[:, 1]
        upper = bb.iloc[:, 2]

        signals = pd.Series(0, index=df.index)
        price = df["close"]
        prev_price = price.shift(1)

        if mode == "reversion":
            # Buy when price touches lower band (mean-reversion up expected)
            signals[(prev_price >= lower.shift(1)) & (price < lower)] = 1
            # Sell when price touches upper band (mean-reversion down expected)
            signals[(prev_price <= upper.shift(1)) & (price > upper)] = -1
        else:
            # Breakout: buy on upper breakout, sell on lower breakdown
            signals[(prev_price <= upper.shift(1)) & (price > upper)] = 1
            signals[(prev_price >= lower.shift(1)) & (price < lower)] = -1

        return signals
