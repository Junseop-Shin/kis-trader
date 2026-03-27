import pandas as pd
from .base import BaseAlgorithm
from .ma_cross import MACrossAlgorithm
from .rsi import RSIAlgorithm
from .macd import MACDAlgorithm
from .bollinger import BollingerAlgorithm
from .momentum import MomentumAlgorithm
from .stochastic import StochasticAlgorithm
from .mean_revert import MeanRevertAlgorithm

ALGO_CLASS_MAP = {
    "MA_CROSS": MACrossAlgorithm,
    "RSI": RSIAlgorithm,
    "MACD": MACDAlgorithm,
    "BOLLINGER": BollingerAlgorithm,
    "MOMENTUM": MomentumAlgorithm,
    "STOCHASTIC": StochasticAlgorithm,
    "MEAN_REVERT": MeanRevertAlgorithm,
}


class MultiAlgorithm(BaseAlgorithm):
    """
    Combine multiple algorithms with AND/OR logic.
    params example:
    {
        "mode": "AND",  # or "OR"
        "algorithms": [
            {"type": "MA_CROSS", "params": {"short_period": 5, "long_period": 20}},
            {"type": "RSI", "params": {"period": 14, "oversold": 30, "overbought": 70}}
        ]
    }
    """

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        mode = self.params.get("mode", "AND")
        algo_configs = self.params.get("algorithms", [])

        if not algo_configs:
            return pd.Series(0, index=df.index)

        all_signals: list[pd.Series] = []
        for config in algo_configs:
            algo_type = config.get("type")
            algo_params = config.get("params", {})
            cls = ALGO_CLASS_MAP.get(algo_type)
            if cls is None:
                continue
            algo = cls(algo_params, {})
            signals = algo.generate_signals(df)
            all_signals.append(signals)

        if not all_signals:
            return pd.Series(0, index=df.index)

        combined = pd.Series(0, index=df.index)

        if mode == "AND":
            # All must agree on BUY / SELL
            buy_mask = pd.Series(True, index=df.index)
            sell_mask = pd.Series(True, index=df.index)
            for s in all_signals:
                buy_mask = buy_mask & (s == 1)
                sell_mask = sell_mask & (s == -1)
            combined[buy_mask] = 1
            combined[sell_mask] = -1
        else:
            # OR: any signal triggers
            for s in all_signals:
                combined[s == 1] = 1
                combined[s == -1] = -1

        return combined
