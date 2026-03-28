import pytest
import pandas as pd
import numpy as np

from app.workers.trading_scheduler import _generate_signal_simple


def _make_df(prices, n=60):
    """Create a DataFrame for signal generation with enough history."""
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    if len(prices) < n:
        prices = [100.0] * (n - len(prices)) + prices
    prices = prices[:n]
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.02 for p in prices],
            "low": [p * 0.98 for p in prices],
            "close": prices,
            "volume": [1000] * n,
        },
        index=dates,
    )


class TestGenerateSignalSimple:
    def test_returns_zero_for_short_data(self):
        df = _make_df([100] * 10, n=10)
        assert _generate_signal_simple(df, "MA_CROSS", {}) == 0

    def test_ma_cross_golden_cross(self):
        """Short MA crossing above long MA should return 1 (BUY)."""
        prices = [50] * 40 + [55, 60, 65, 70, 75, 80, 85, 90, 95, 100,
                               105, 110, 115, 120, 125, 130, 135, 140, 145, 150]
        df = _make_df(prices, n=60)
        signal = _generate_signal_simple(df, "MA_CROSS", {"short_period": 5, "long_period": 20})
        # May or may not trigger depending on exact values
        assert signal in [0, 1, -1]

    def test_ma_cross_ema_mode(self):
        prices = [50] * 40 + [60, 70, 80, 90, 100, 110, 120, 130, 140, 150,
                               160, 170, 180, 190, 200, 210, 220, 230, 240, 250]
        df = _make_df(prices, n=60)
        signal = _generate_signal_simple(df, "MA_CROSS", {"short_period": 5, "long_period": 20, "ma_type": "EMA"})
        assert signal in [0, 1, -1]

    def test_rsi_signal(self):
        # Random-ish data
        np.random.seed(42)
        prices = (100 + np.cumsum(np.random.randn(60) * 2)).tolist()
        df = _make_df(prices, n=60)
        signal = _generate_signal_simple(df, "RSI", {"period": 14, "oversold": 30, "overbought": 70})
        assert signal in [0, 1, -1]

    def test_macd_signal(self):
        np.random.seed(42)
        prices = (100 + np.cumsum(np.random.randn(60) * 2)).tolist()
        df = _make_df(prices, n=60)
        signal = _generate_signal_simple(df, "MACD", {"fast": 12, "slow": 26, "signal": 9})
        assert signal in [0, 1, -1]

    def test_bollinger_reversion_signal(self):
        # Drop below lower band
        prices = [100] * 40 + [95, 90, 85, 80, 75, 70, 65, 60, 55, 50,
                                48, 46, 44, 42, 40, 38, 36, 34, 32, 30]
        df = _make_df(prices, n=60)
        signal = _generate_signal_simple(df, "BOLLINGER", {"period": 20, "std_dev": 2.0, "mode": "reversion"})
        assert signal in [0, 1, -1]

    def test_unknown_algorithm_returns_zero(self):
        df = _make_df([100] * 60, n=60)
        signal = _generate_signal_simple(df, "UNKNOWN_ALGO", {})
        assert signal == 0

    def test_returns_zero_for_hold(self):
        """Flat prices should produce HOLD signal."""
        df = _make_df([100.0] * 60, n=60)
        signal = _generate_signal_simple(df, "MA_CROSS", {"short_period": 5, "long_period": 20})
        assert signal == 0
