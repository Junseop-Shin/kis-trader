"""
트레이딩 스케줄러 미커버 경로 테스트
BUY 신호 주문 생성 경로, SIM 주문 ValueError 처리, REAL 주문 비200 응답 등
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
import numpy as np


def _make_activation(tickers=None):
    from app.models.trading import ActivationStatus
    act = MagicMock()
    act.id = 1
    act.strategy_id = 1
    act.account_id = 1
    act.tickers = tickers or ["005930"]
    act.status = ActivationStatus.ACTIVE
    act.last_signal_date = None
    act.last_signal_action = None
    return act


def _make_strategy(algo="MA_CROSS"):
    strat = MagicMock()
    strat.id = 1
    strat.name = "Test"
    strat.algorithm_type.value = algo
    strat.params = {"short_period": 3, "long_period": 5, "ma_type": "SMA"}
    strat.trade_params = {"position_size_pct": 0.1}
    return strat


def _make_account(cash=10_000_000, acct_type="SIM"):
    acc = MagicMock()
    acc.id = 1
    acc.user_id = 1
    acc.cash_balance = cash
    acc.type.value = acct_type
    acc.is_active = True
    return acc


def _golden_cross_price_rows():
    """골든크로스 유발 가격 데이터 (검증된 패턴)"""
    prices = np.array([70000.0] * 25 + [65000.0, 63000.0, 61000.0, 75000.0, 80000.0])
    n = len(prices)
    dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
    return [
        (dates[i], float(prices[i]) - 200, float(prices[i]) + 500,
         float(prices[i]) - 500, float(prices[i]), 1_000_000.0)
        for i in range(n)
    ]


class TestBuySignalOrderCreation:
    """BUY 신호 발생 시 주문 생성 경로 테스트"""

    async def test_buy_signal_creates_pending_order(self):
        """BUY 신호 → PENDING 주문 생성 및 Slack 알림"""
        activation = _make_activation()
        strategy = _make_strategy()
        account = _make_account(cash=10_000_000)

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        price_result = MagicMock()
        price_result.fetchall.return_value = _golden_cross_price_rows()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result, price_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("app.workers.trading_scheduler.SlackService") as mock_slack_cls:
                mock_slack_cls.return_value = MagicMock()
                from app.workers.trading_scheduler import generate_signals_and_queue_orders
                await generate_signals_and_queue_orders()

        # BUY 신호가 발생하면 Order가 추가됨
        mock_session.add.assert_called_once()
        mock_slack_cls.return_value.send_trade_signal.assert_called_once()

    async def test_buy_signal_zero_qty_skips(self):
        """BUY 신호 + 현금 부족으로 qty=0 → 주문 미생성"""
        activation = _make_activation()
        strategy = _make_strategy()
        # 현금 100원 → qty = int(100 * 0.1 / 80000) = 0
        account = _make_account(cash=100)

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        price_result = MagicMock()
        price_result.fetchall.return_value = _golden_cross_price_rows()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result, price_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import generate_signals_and_queue_orders
            await generate_signals_and_queue_orders()

        # qty=0 → 주문 미생성
        mock_session.add.assert_not_called()

    async def test_unexpected_signal_value_hits_else_continue(self):
        """비정상 신호 값(2) → else: continue (line 220) 실행 → 주문 미생성"""
        from unittest.mock import patch as _patch
        activation = _make_activation()
        strategy = _make_strategy()
        account = _make_account(cash=10_000_000)

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        price_result = MagicMock()
        price_result.fetchall.return_value = _golden_cross_price_rows()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result, price_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        # signal=2 is not 0/1/-1 → hits else: continue at line 220
        with _patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with _patch("app.workers.trading_scheduler._generate_signal_simple", return_value=2):
                from app.workers.trading_scheduler import generate_signals_and_queue_orders
                await generate_signals_and_queue_orders()

        # unexpected signal → 주문 미생성
        mock_session.add.assert_not_called()


class TestSignalGenerationException:
    """신호 생성 루프 내 예외 처리 테스트"""

    async def test_signal_generation_inner_exception_continues(self):
        """신호 생성 중 전략 조회 예외 → 해당 activation 건너뜀 (lines 247-249 커버)"""
        from app.models.trading import ActivationStatus

        activation = MagicMock()
        activation.id = 1
        activation.strategy_id = 1
        activation.account_id = 1
        activation.tickers = ["005930"]
        activation.status = ActivationStatus.ACTIVE
        activation.last_signal_date = None
        activation.last_signal_action = None

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        mock_session = AsyncMock()
        # 첫 번째 execute: activation 목록, 두 번째: 전략 조회 예외 발생 → 라인 247-249 실행
        mock_session.execute = AsyncMock(side_effect=[act_result, Exception("DB error")])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import generate_signals_and_queue_orders
            # 예외가 외부로 전파되지 않아야 함
            await generate_signals_and_queue_orders()

        # 예외 발생해도 commit은 정상 호출
        mock_session.commit.assert_awaited_once()


class TestSimOrderValueError:
    """SIM 주문 실행 중 ValueError 처리 테스트"""

    def _make_order(self, side="BUY"):
        from app.models.account import OrderStatus
        order = MagicMock()
        order.id = 1
        order.ticker = "005930"
        order.side.value = side
        order.qty = 10
        order.price = 70000.0
        order.account_id = 1
        order.strategy_activation_id = 1
        order.status = OrderStatus.PENDING
        return order

    async def test_sim_order_value_error_marks_failed(self):
        """SIM 주문에서 ValueError 발생 → FAILED 처리"""
        from app.models.account import OrderStatus
        order = self._make_order()
        account = _make_account(acct_type="SIM")

        order_result = MagicMock()
        order_result.scalars.return_value.all.return_value = [order]

        price_result = MagicMock()
        price_result.fetchone.return_value = (70500,)

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[order_result, price_result, acct_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("app.workers.trading_scheduler.place_sim_order", new_callable=AsyncMock) as mock_place:
                mock_place.side_effect = ValueError("Insufficient balance")
                from app.workers.trading_scheduler import execute_pending_orders
                await execute_pending_orders()

        # ValueError → FAILED
        assert order.status == OrderStatus.FAILED

    async def test_order_execution_outer_exception(self):
        """주문 처리 중 예상치 못한 예외 발생 → 주문 FAILED 처리"""
        from app.models.account import OrderStatus
        order = self._make_order()

        order_result = MagicMock()
        order_result.scalars.return_value.all.return_value = [order]

        mock_session = AsyncMock()
        # 가격 조회 시 예외 발생 (내부 try-except 외부에서)
        mock_session.execute = AsyncMock(side_effect=[order_result, Exception("Unexpected DB error")])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import execute_pending_orders
            await execute_pending_orders()

        # 외부 예외 → FAILED
        assert order.status == OrderStatus.FAILED

    async def test_real_order_non_200_marks_failed(self):
        """REAL 주문에서 비200 응답 → FAILED 처리"""
        from app.models.account import OrderStatus
        order = self._make_order()
        account = _make_account(acct_type="REAL")

        order_result = MagicMock()
        order_result.scalars.return_value.all.return_value = [order]

        price_result = MagicMock()
        price_result.fetchone.return_value = (70500,)

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[order_result, price_result, acct_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        # 500 응답 mock
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("httpx.AsyncClient") as mock_http_cls:
                mock_http = AsyncMock()
                mock_http.post = AsyncMock(return_value=mock_response)
                mock_http_cls.return_value.__aenter__.return_value = mock_http
                from app.workers.trading_scheduler import execute_pending_orders
                await execute_pending_orders()

        assert order.status == OrderStatus.FAILED
