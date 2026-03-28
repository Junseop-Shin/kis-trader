import pandas as pd
import numpy as np
from .base import BaseAlgorithm


class MeanRevertAlgorithm(BaseAlgorithm):
    """Z-score mean reversion strategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        lookback = self.params.get("lookback", 20)
        entry_z = self.params.get("entry_z", -2.0)
        exit_z = self.params.get("exit_z", 0.0)

        rolling_mean = df["close"].rolling(lookback).mean()
        rolling_std = df["close"].rolling(lookback).std()

        z_score = (df["close"] - rolling_mean) / rolling_std.replace(0, np.nan)
        prev_z = z_score.shift(1)

        signals = pd.Series(0, index=df.index)

        # Buy when z-score drops below entry threshold (price is cheap)
        signals[(prev_z >= entry_z) & (z_score < entry_z)] = 1
        # Sell when z-score crosses above exit threshold (back to mean)
        signals[(prev_z <= exit_z) & (z_score > exit_z)] = -1

        return signals
