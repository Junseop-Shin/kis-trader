from .base import BaseAlgorithm, TradeRecord, BacktestMetrics
from .ma_cross import MACrossAlgorithm
from .rsi import RSIAlgorithm
from .macd import MACDAlgorithm
from .bollinger import BollingerAlgorithm
from .momentum import MomentumAlgorithm
from .stochastic import StochasticAlgorithm
from .mean_revert import MeanRevertAlgorithm
from .multi import MultiAlgorithm

ALGORITHM_MAP = {
    "MA_CROSS": MACrossAlgorithm,
    "RSI": RSIAlgorithm,
    "MACD": MACDAlgorithm,
    "BOLLINGER": BollingerAlgorithm,
    "MOMENTUM": MomentumAlgorithm,
    "STOCHASTIC": StochasticAlgorithm,
    "MEAN_REVERT": MeanRevertAlgorithm,
    "MULTI": MultiAlgorithm,
}

__all__ = [
    "BaseAlgorithm", "TradeRecord", "BacktestMetrics",
    "MACrossAlgorithm", "RSIAlgorithm", "MACDAlgorithm",
    "BollingerAlgorithm", "MomentumAlgorithm", "StochasticAlgorithm",
    "MeanRevertAlgorithm", "MultiAlgorithm",
    "ALGORITHM_MAP",
]
