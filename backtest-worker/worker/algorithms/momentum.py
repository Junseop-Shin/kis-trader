import pandas as pd
from .base import BaseAlgorithm


class MomentumAlgorithm(BaseAlgorithm):
    """Rate of Change (ROC) momentum strategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get("period", 12)
        buy_threshold = self.params.get("buy_threshold", 0.0)
        sell_threshold = self.params.get("sell_threshold", 0.0)

        roc = df["close"].pct_change(periods=period) * 100
        prev_roc = roc.shift(1)

        signals = pd.Series(0, index=df.index)

        # Buy when ROC crosses above buy_threshold
        signals[(prev_roc <= buy_threshold) & (roc > buy_threshold)] = 1
        # Sell when ROC crosses below sell_threshold
        signals[(prev_roc >= sell_threshold) & (roc < sell_threshold)] = -1

        return signals
