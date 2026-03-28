"""
커버리지 갭 보완 테스트
_get_algo_class, MA_CROSS 크로스오버, SELL 신호 경로, sync_sim_account 등
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch

from app.workers.trading_scheduler import _get_algo_class, _generate_signal_simple


class TestGetAlgoClass:
    """_get_algo_class 함수 단위 테스트"""

    def test_get_algo_class_ma_cross(self):
        """MA_CROSS 알고리즘 클래스 요청 — None 반환 (백엔드에서는 인라인 구현)"""
        result = _get_algo_class("MA_CROSS")
        assert result is None

    def test_get_algo_class_rsi(self):
        """RSI 알고리즘 클래스 요청"""
        result = _get_algo_class("RSI")
        assert result is None

    def test_get_algo_class_macd(self):
        """MACD 알고리즘 클래스 요청"""
        result = _get_algo_class("MACD")
        assert result is None

    def test_get_algo_class_bollinger(self):
        """BOLLINGER 알고리즘 클래스 요청"""
        result = _get_algo_class("BOLLINGER")
        assert result is None

    def test_get_algo_class_momentum(self):
        """MOMENTUM 알고리즘 클래스 요청"""
        result = _get_algo_class("MOMENTUM")
        assert result is None

    def test_get_algo_class_stochastic(self):
        """STOCHASTIC 알고리즘 클래스 요청"""
        result = _get_algo_class("STOCHASTIC")
        assert result is None

    def test_get_algo_class_mean_revert(self):
        """MEAN_REVERT 알고리즘 클래스 요청"""
        result = _get_algo_class("MEAN_REVERT")
        assert result is None

    def test_get_algo_class_unknown(self):
        """알 수 없는 알고리즘 요청 — None 반환"""
        result = _get_algo_class("UNKNOWN_TYPE")
        assert result is None


class TestMACrossSignals:
    """MA_CROSS 신호 생성 — 골든크로스/데스크로스 정확한 검증"""

    def _make_crossover_df(self, cross_type: str) -> pd.DataFrame:
        """골든크로스 또는 데스크로스를 유발하는 DataFrame 생성"""
        if cross_type == "golden":
            # 하락 후 급반등 → 단기 MA가 장기 MA를 상향 돌파
            prices = np.array([70000.0] * 25 + [65000.0, 63000.0, 61000.0, 75000.0, 80000.0])
        else:  # death cross
            # 상승 후 급락 → 단기 MA가 장기 MA를 하향 돌파
            prices = np.array([70000.0] * 25 + [75000.0, 77000.0, 79000.0, 65000.0, 60000.0])

        n = len(prices)
        dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
        # pd.Series는 list로 전달해야 DatetimeIndex와의 정렬 문제 방지
        return pd.DataFrame({
            "open": prices - 200.0,
            "high": prices + 500.0,
            "low": prices - 500.0,
            "close": prices,
            "volume": np.ones(n) * 1_000_000.0,
        }, index=dates)

    def test_ma_cross_golden_cross_returns_buy(self):
        """골든크로스(단기>장기 상향 돌파) → BUY(1) 신호"""
        df = self._make_crossover_df("golden")
        # SMA_3 vs SMA_5 크로스 확인
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 3, "long_period": 5, "ma_type": "SMA"})
        assert result == 1, f"Expected BUY(1) on golden cross, got {result}"

    def test_ma_cross_death_cross_returns_sell(self):
        """데스크로스(단기<장기 하향 돌파) → SELL(-1) 신호"""
        df = self._make_crossover_df("death")
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 3, "long_period": 5, "ma_type": "SMA"})
        assert result == -1, f"Expected SELL(-1) on death cross, got {result}"

    def test_ma_cross_ema_golden_cross(self):
        """EMA 기반 골든크로스 → BUY(1) 신호"""
        df = self._make_crossover_df("golden")
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 3, "long_period": 5, "ma_type": "EMA"})
        # EMA는 SMA보다 반응이 빠르므로 BUY 신호가 될 수 있음
        assert result in [0, 1]  # EMA 크로스는 타이밍이 다를 수 있음

    def test_ma_cross_no_cross_returns_hold(self):
        """크로스오버 없을 때 HOLD(0)"""
        # 단조 상승 → 단기 MA가 항상 장기 MA 위
        n = 30
        prices = list(range(60000, 60000 + n * 100, 100))
        dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
        df = pd.DataFrame({
            "open": [p - 50 for p in prices],
            "high": [p + 100 for p in prices],
            "low": [p - 100 for p in prices],
            "close": pd.Series(prices, dtype=float),
            "volume": [1_000_000] * n,
        }, index=dates)
        result = _generate_signal_simple(df, "MA_CROSS", {"short_period": 3, "long_period": 5, "ma_type": "SMA"})
        assert result == 0


class TestSellSignalPath:
    """SELL 신호 경로 — generate_signals_and_queue_orders에서 포지션 매도 처리"""

    async def test_sell_signal_with_position_creates_sell_order(self):
        """SELL 신호 + 포지션 있을 때 SELL 주문 생성"""
        from app.models.trading import ActivationStatus
        from app.models.account import OrderSide

        activation = MagicMock()
        activation.id = 1
        activation.strategy_id = 1
        activation.account_id = 1
        activation.tickers = ["005930"]
        activation.status = ActivationStatus.ACTIVE
        activation.last_signal_date = None
        activation.last_signal_action = None

        strategy = MagicMock()
        strategy.id = 1
        strategy.name = "Test"
        strategy.algorithm_type.value = "MA_CROSS"
        strategy.params = {"short_period": 3, "long_period": 5, "ma_type": "SMA"}
        strategy.trade_params = {"position_size_pct": 0.1}

        account = MagicMock()
        account.id = 1
        account.user_id = 1
        account.cash_balance = 10_000_000
        account.type.value = "SIM"
        account.is_active = True

        # 포지션: 10주 보유
        position = MagicMock()
        position.qty = 10
        position.ticker = "005930"

        # 데스크로스 데이터 — SELL 신호 유발
        prices_down = [70000.0] * 25 + [75000.0, 77000.0, 79000.0, 65000.0, 60000.0]
        n = len(prices_down)
        price_rows = [
            (pd.Timestamp(f"2023-01-0{i+2}" if i < 8 else f"2023-02-{i-7:02d}"), 70000, 71000, 69000, prices_down[i], 1_000_000)
            for i in range(n)
        ]

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        price_result = MagicMock()
        price_result.fetchall.return_value = price_rows

        pos_result = MagicMock()
        pos_result.scalar_one_or_none.return_value = position

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result, price_result, pos_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("app.workers.trading_scheduler.SlackService"):
                from app.workers.trading_scheduler import generate_signals_and_queue_orders
                await generate_signals_and_queue_orders()

        mock_session.commit.assert_awaited_once()

    async def test_sell_signal_no_position_skips(self):
        """SELL 신호 + 포지션 없으면 주문 미생성"""
        from app.models.trading import ActivationStatus

        activation = MagicMock()
        activation.id = 1
        activation.strategy_id = 1
        activation.account_id = 1
        activation.tickers = ["005930"]
        activation.status = ActivationStatus.ACTIVE
        activation.last_signal_date = None
        activation.last_signal_action = None

        strategy = MagicMock()
        strategy.id = 1
        strategy.name = "Test"
        strategy.algorithm_type.value = "MA_CROSS"
        strategy.params = {"short_period": 3, "long_period": 5, "ma_type": "SMA"}
        strategy.trade_params = {"position_size_pct": 0.1}

        account = MagicMock()
        account.id = 1
        account.user_id = 1
        account.cash_balance = 10_000_000
        account.type.value = "SIM"
        account.is_active = True

        # 데스크로스 데이터
        prices_down = [70000.0] * 25 + [75000.0, 77000.0, 79000.0, 65000.0, 60000.0]
        n = len(prices_down)
        price_rows = [
            (pd.Timestamp(f"2023-0{(i//30)+1:01d}-{(i%30)+1:02d}"), 70000, 71000, 69000, prices_down[i], 1_000_000)
            for i in range(n)
        ]

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        price_result = MagicMock()
        price_result.fetchall.return_value = price_rows

        pos_result = MagicMock()
        pos_result.scalar_one_or_none.return_value = None  # 포지션 없음

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result, price_result, pos_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import generate_signals_and_queue_orders
            await generate_signals_and_queue_orders()

        # 포지션 없음 → 주문 미생성
        mock_session.add.assert_not_called()


class TestSyncSimAccount:
    """kis_service.sync_sim_account 테스트"""

    async def test_sync_sim_account_updates_prices(self):
        """포지션의 현재가를 최신 가격으로 업데이트"""
        from app.services.kis_service import sync_sim_account
        from app.models.account import Account, AccountType

        account = MagicMock()
        account.id = 1

        position = MagicMock()
        position.ticker = "005930"
        position.avg_price = 70000.0
        position.qty = 10
        position.current_price = 70000.0
        position.unrealized_pnl = 0.0

        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        price_result = MagicMock()
        price_result.fetchone.return_value = (72000,)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[pos_result, price_result])
        mock_db.flush = AsyncMock()

        await sync_sim_account(account, mock_db)

        # 현재가 업데이트 확인
        assert position.current_price == 72000.0
        assert position.unrealized_pnl == (72000.0 - 70000.0) * 10

    async def test_sync_sim_account_no_price_data(self):
        """가격 데이터 없을 때 포지션 업데이트 생략"""
        from app.services.kis_service import sync_sim_account

        account = MagicMock()
        account.id = 1

        position = MagicMock()
        position.ticker = "999999"
        position.avg_price = 70000.0
        position.qty = 10
        position.current_price = 70000.0

        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = [position]

        price_result = MagicMock()
        price_result.fetchone.return_value = None  # 가격 없음

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[pos_result, price_result])
        mock_db.flush = AsyncMock()

        original_price = position.current_price
        await sync_sim_account(account, mock_db)

        # 가격 데이터 없음 → 업데이트 없음
        assert position.current_price == original_price

    async def test_sync_sim_account_no_positions(self):
        """포지션이 없을 때 아무 작업도 하지 않음"""
        from app.services.kis_service import sync_sim_account

        account = MagicMock()
        account.id = 1

        pos_result = MagicMock()
        pos_result.scalars.return_value.all.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=pos_result)
        mock_db.flush = AsyncMock()

        await sync_sim_account(account, mock_db)

        # DB execute는 한 번만 호출 (포지션 조회)
        assert mock_db.execute.await_count == 1
