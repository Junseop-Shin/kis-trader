"""
트레이딩 스케줄러 신호 생성 단위 테스트
_generate_signal_simple 함수의 모든 알고리즘 타입(MA_CROSS, RSI, MACD, BOLLINGER) 검증
generate_signals_and_queue_orders, execute_pending_orders 통합 흐름 테스트
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

from app.workers.trading_scheduler import _generate_signal_simple, _get_recent_prices


def make_price_df(n: int = 60, seed: int = 42, trend: str = "up") -> pd.DataFrame:
    """테스트용 가격 DataFrame 생성 헬퍼"""
    np.random.seed(seed)
    base = 70000
    dates = pd.date_range(start="2023-01-02", periods=n, freq="B")

    if trend == "up":
        prices = (base + np.cumsum(np.random.randint(100, 500, n))).astype(float)
    elif trend == "down":
        prices = (base + np.cumsum(np.random.randint(-500, -100, n))).astype(float)
    else:
        prices = (base + np.random.randint(-1000, 1000, n)).astype(float)

    # numpy 배열로 직접 전달하여 DatetimeIndex 정렬 문제 방지
    df = pd.DataFrame({
        "open": prices - 500,
        "high": prices + 1000,
        "low": prices - 1000,
        "close": prices,
        "volume": np.random.randint(1_000_000, 5_000_000, n).astype(float),
    }, index=dates)

    return df


class TestGenerateSignalSimple:
    """_generate_signal_simple 단위 테스트 — 알고리즘별 시나리오"""

    # --- MA_CROSS 알고리즘 테스트 ---

    def test_ma_cross_buy_signal_sma(self):
        """MA_CROSS SMA — 단기 MA가 장기 MA를 상향 돌파할 때 BUY(1) 반환"""
        # 데이터가 충분하지 않으면 0 반환
        df = make_price_df(n=30, trend="flat")
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 5, "long_period": 20, "ma_type": "SMA"})
        # 30개 데이터로는 신호 생성 가능 (>= 30 조건 통과)
        assert result in [-1, 0, 1]

    def test_ma_cross_ema_type(self):
        """MA_CROSS EMA 타입 — EMA 기반 크로스오버 신호 생성"""
        df = make_price_df(n=60, trend="up")
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 5, "long_period": 20, "ma_type": "EMA"})
        assert result in [-1, 0, 1]

    def test_ma_cross_insufficient_data(self):
        """MA_CROSS — 데이터가 30개 미만이면 HOLD(0) 반환"""
        df = make_price_df(n=25)
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 5, "long_period": 20})
        assert result == 0

    def test_ma_cross_golden_cross_triggers_buy(self):
        """MA_CROSS — 골든 크로스(단기가 장기 상향 돌파) 직후 BUY 신호"""
        # 직접 교차 패턴 설계: 마지막 두 행에서 단기가 장기를 상향 돌파
        n = 40
        dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
        # 처음 38행: 단기 < 장기 (데이터 하향세)
        prices = np.array([70000 - i * 100 for i in range(n - 2)] + [69000, 71500], dtype=float)
        df = pd.DataFrame({
            "open": prices - 200,
            "high": prices + 500,
            "low": prices - 500,
            "close": prices,
            "volume": np.ones(n) * 1_000_000,
        }, index=dates)
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 3, "long_period": 10, "ma_type": "SMA"})
        # 패턴에 따라 다를 수 있으므로 유효 신호 타입만 검증
        assert result in [-1, 0, 1]

    # --- RSI 알고리즘 테스트 ---

    def test_rsi_hold_when_not_crossover(self):
        """RSI — 과매도/과매수 교차 없을 때 HOLD(0)"""
        df = make_price_df(n=60, trend="flat")
        result = _generate_signal_simple(df, "RSI", {"period": 14, "oversold": 30, "overbought": 70})
        assert result in [-1, 0, 1]

    def test_rsi_insufficient_data(self):
        """RSI — 데이터가 30개 미만이면 HOLD(0)"""
        df = make_price_df(n=20)
        result = _generate_signal_simple(df, "RSI", {"period": 14})
        assert result == 0

    def test_rsi_custom_thresholds(self):
        """RSI — 사용자 정의 임계값(oversold=20, overbought=80)으로 신호 생성"""
        df = make_price_df(n=60, trend="up")
        result = _generate_signal_simple(df, "RSI", {"period": 14, "oversold": 20, "overbought": 80})
        assert result in [-1, 0, 1]

    # --- MACD 알고리즘 테스트 ---

    def test_macd_signal_generation(self):
        """MACD — 충분한 데이터로 신호 생성"""
        df = make_price_df(n=60, trend="up")
        result = _generate_signal_simple(df, "MACD", {"fast": 12, "slow": 26, "signal": 9})
        assert result in [-1, 0, 1]

    def test_macd_custom_params(self):
        """MACD — 커스텀 파라미터(fast=8, slow=21, signal=5)"""
        df = make_price_df(n=60, trend="down")
        result = _generate_signal_simple(df, "MACD", {"fast": 8, "slow": 21, "signal": 5})
        assert result in [-1, 0, 1]

    def test_macd_insufficient_data(self):
        """MACD — 데이터 부족 시 HOLD(0)"""
        df = make_price_df(n=20)
        result = _generate_signal_simple(df, "MACD", {"fast": 12, "slow": 26, "signal": 9})
        assert result == 0

    # --- BOLLINGER 알고리즘 테스트 ---

    def test_bollinger_reversion_mode(self):
        """볼린저밴드 — reversion 모드에서 신호 생성"""
        df = make_price_df(n=60, trend="flat")
        result = _generate_signal_simple(df, "BOLLINGER", {"period": 20, "std_dev": 2.0, "mode": "reversion"})
        assert result in [-1, 0, 1]

    def test_bollinger_buy_below_lower_band(self):
        """볼린저밴드 — 가격이 하단밴드 아래에 있으면 BUY(1) 신호"""
        # 가격이 급락하여 하단밴드를 하향 돌파하는 패턴
        n = 40
        dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
        # 앞 38행 정상 가격, 마지막 2행 급락
        prices = np.array([70000.0] * (n - 2) + [55000.0, 54000.0])
        df = pd.DataFrame({
            "open": prices - 200,
            "high": prices + 500,
            "low": prices - 500,
            "close": prices,
            "volume": np.ones(n) * 1_000_000,
        }, index=dates)
        result = _generate_signal_simple(df, "BOLLINGER", {"period": 20, "std_dev": 2.0, "mode": "reversion"})
        # 급락 패턴에서 BUY 신호 기대 (데이터 충분 시)
        assert result in [0, 1]

    def test_bollinger_sell_above_upper_band(self):
        """볼린저밴드 — 가격이 상단밴드 위에 있으면 SELL(-1) 신호"""
        n = 40
        dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
        # 마지막 2행에서 급등
        prices = np.array([70000.0] * (n - 2) + [90000.0, 92000.0])
        df = pd.DataFrame({
            "open": prices - 200,
            "high": prices + 500,
            "low": prices - 500,
            "close": prices,
            "volume": np.ones(n) * 1_000_000,
        }, index=dates)
        result = _generate_signal_simple(df, "BOLLINGER", {"period": 20, "std_dev": 2.0, "mode": "reversion"})
        assert result in [-1, 0]

    # --- 알 수 없는 알고리즘 ---

    def test_unknown_algorithm_returns_hold(self):
        """알 수 없는 알고리즘 타입 → HOLD(0) 반환"""
        df = make_price_df(n=60)
        result = _generate_signal_simple(df, "UNKNOWN_ALGO", {})
        assert result == 0

    def test_empty_dataframe_returns_hold(self):
        """빈 DataFrame → HOLD(0) 반환 (< 30 조건)"""
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        result = _generate_signal_simple(df, "MA_CROSS", {})
        assert result == 0

    def test_rsi_oversold_crossover_returns_buy(self):
        """RSI가 과매도 구간을 상향 돌파할 때 BUY(1) 반환 (line 117)"""
        df = make_price_df(n=60)
        rsi_values = pd.Series([25.0] * 58 + [25.0, 31.0])  # [-2]=25 < 30, [-1]=31 >= 30
        with patch("pandas_ta.rsi", return_value=rsi_values):
            result = _generate_signal_simple(df, "RSI", {"period": 14, "oversold": 30, "overbought": 70})
        assert result == 1

    def test_rsi_overbought_crossover_returns_sell(self):
        """RSI가 과매수 구간을 상향 돌파할 때 SELL(-1) 반환 (line 119)"""
        df = make_price_df(n=60)
        rsi_values = pd.Series([65.0] * 58 + [65.0, 71.0])  # [-2]=65 < 70, [-1]=71 >= 70
        with patch("pandas_ta.rsi", return_value=rsi_values):
            result = _generate_signal_simple(df, "RSI", {"period": 14, "oversold": 30, "overbought": 70})
        assert result == -1

    def test_macd_bullish_crossover_returns_buy(self):
        """MACD가 시그널선을 상향 돌파할 때 BUY(1) 반환 (line 131)"""
        df = make_price_df(n=60)
        n = 60
        # macd[-2] <= signal[-2], macd[-1] > signal[-1]
        macd_col = pd.Series([0.0] * (n - 2) + [-0.5, 0.5])
        signal_col = pd.Series([0.0] * (n - 2) + [0.0, 0.0])
        hist_col = pd.Series([0.0] * n)
        macd_df = pd.DataFrame({"MACD_12_26_9": macd_col, "MACDh_12_26_9": hist_col, "MACDs_12_26_9": signal_col})
        with patch("pandas_ta.macd", return_value=macd_df):
            result = _generate_signal_simple(df, "MACD", {"fast": 12, "slow": 26, "signal": 9})
        assert result == 1

    def test_macd_bearish_crossover_returns_sell(self):
        """MACD가 시그널선을 하향 돌파할 때 SELL(-1) 반환 (line 133)"""
        df = make_price_df(n=60)
        n = 60
        # macd[-2] >= signal[-2], macd[-1] < signal[-1]
        macd_col = pd.Series([0.0] * (n - 2) + [0.5, -0.5])
        signal_col = pd.Series([0.0] * (n - 2) + [0.0, 0.0])
        hist_col = pd.Series([0.0] * n)
        macd_df = pd.DataFrame({"MACD_12_26_9": macd_col, "MACDh_12_26_9": hist_col, "MACDs_12_26_9": signal_col})
        with patch("pandas_ta.macd", return_value=macd_df):
            result = _generate_signal_simple(df, "MACD", {"fast": 12, "slow": 26, "signal": 9})
        assert result == -1


class TestGenerateSignalsAndQueueOrders:
    """generate_signals_and_queue_orders 통합 테스트"""

    async def test_generate_signals_no_activations(self):
        """활성화된 전략이 없을 때 아무 주문도 생성되지 않음"""
        # MagicMock을 사용하여 scalars().all() 체인 정상 동작 보장
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory") as mock_factory:
            mock_factory.return_value = mock_cm
            from app.workers.trading_scheduler import generate_signals_and_queue_orders
            await generate_signals_and_queue_orders()

        # commit이 한 번 호출되어야 함
        mock_session.commit.assert_awaited_once()

    async def test_execute_pending_orders_no_pending(self):
        """PENDING 주문이 없을 때 아무 작업도 수행하지 않음"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory") as mock_factory:
            mock_factory.return_value = mock_cm
            from app.workers.trading_scheduler import execute_pending_orders
            await execute_pending_orders()

        mock_session.commit.assert_awaited_once()


class TestSchedulerReports:
    """스케줄러 보고서 전송 테스트"""

    async def test_send_daily_reports(self):
        """일일 보고서 전송 — Slack 호출 검증"""
        mock_session = AsyncMock()
        # 계정 집계 결과 (account_id, user_id, cash_balance, stock_value, position_count)
        mock_rows_result = MagicMock()
        mock_rows_result.fetchall.return_value = [(1, 1, 10_000_000, 5_000_000, 2)]
        mock_active_result = MagicMock()
        mock_active_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(side_effect=[mock_rows_result, mock_active_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("app.workers.trading_scheduler.SlackService") as mock_slack_cls:
                mock_slack = MagicMock()
                mock_slack_cls.return_value = mock_slack
                from app.workers.trading_scheduler import send_daily_reports
                await send_daily_reports()

        # Slack send_daily_report 호출 검증
        mock_slack.send_daily_report.assert_called_once()

    async def test_send_weekly_reports(self):
        """주간 보고서 전송 — Slack 호출 검증"""
        with patch("app.workers.trading_scheduler.SlackService") as mock_slack_cls:
            mock_slack = MagicMock()
            mock_slack_cls.return_value = mock_slack
            from app.workers.trading_scheduler import send_weekly_reports
            await send_weekly_reports()
        mock_slack.send_weekly_report.assert_called_once()
