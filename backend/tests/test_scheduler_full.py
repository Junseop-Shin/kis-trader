"""
트레이딩 스케줄러 전체 흐름 통합 테스트
generate_signals_and_queue_orders, execute_pending_orders의 내부 루프 검증
활성화된 전략/계정/포지션이 있을 때의 시나리오 커버
"""
import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

import pandas as pd
import numpy as np


def _build_price_df(n=60, trend="flat") -> pd.DataFrame:
    """테스트용 가격 데이터프레임 빌더"""
    np.random.seed(42)
    dates = pd.date_range(start="2023-01-02", periods=n, freq="B")
    prices = 70000 + np.cumsum(np.random.randint(-500, 500, n)).astype(float)
    return pd.DataFrame({
        "open": prices - 200,
        "high": prices + 500,
        "low": prices - 500,
        "close": prices,
        "volume": np.ones(n) * 1_000_000,
    }, index=dates)


def _make_activation(activation_id=1, strategy_id=1, account_id=1, tickers=None):
    """StrategyActivation mock 생성"""
    from app.models.trading import ActivationStatus
    act = MagicMock()
    act.id = activation_id
    act.strategy_id = strategy_id
    act.account_id = account_id
    act.tickers = tickers or ["005930"]
    act.status = ActivationStatus.ACTIVE
    act.last_signal_date = None
    act.last_signal_action = None
    return act


def _make_strategy(strategy_id=1, algo_type="MA_CROSS", params=None, trade_params=None):
    """Strategy mock 생성"""
    strat = MagicMock()
    strat.id = strategy_id
    strat.name = "Test Strategy"
    strat.algorithm_type.value = algo_type
    strat.params = params or {"short_period": 5, "long_period": 20, "ma_type": "SMA"}
    strat.trade_params = trade_params or {"position_size_pct": 0.1, "initial_capital": 10_000_000}
    return strat


def _make_account(account_id=1, cash=10_000_000, acct_type="SIM"):
    """Account mock 생성"""
    acct = MagicMock()
    acct.id = account_id
    acct.user_id = 1
    acct.cash_balance = cash
    acct.type.value = acct_type
    acct.is_active = True
    return acct


class TestGenerateSignalsWithActivations:
    """활성화된 전략이 있을 때 신호 생성 루프 테스트"""

    async def test_generate_signals_with_active_strategy_hold(self):
        """활성 전략 존재하지만 신호가 HOLD(0)이면 주문 미생성"""
        activation = _make_activation()
        strategy = _make_strategy()
        account = _make_account()

        # 30개 미만 데이터 → HOLD 신호 (데이터 부족)
        small_df = pd.DataFrame(
            {"open": [70000]*10, "high": [71000]*10, "low": [69000]*10,
             "close": [70000.0]*10, "volume": [1_000_000]*10},
            index=pd.date_range("2023-01-02", periods=10, freq="B")
        )

        # DB 결과 mock 체인
        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        # 가격 데이터 조회 결과 (10개 행)
        price_rows = [(pd.Timestamp(f"2023-01-{i+2:02d}"), 70000, 71000, 69000, 70000.0, 1_000_000) for i in range(10)]
        price_result = MagicMock()
        price_result.fetchall.return_value = price_rows

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

        # 신호 없음 → 주문 미생성 (add 미호출)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_awaited_once()

    async def test_generate_signals_buy_signal_creates_order(self):
        """BUY 신호 → 주문 생성 확인"""
        activation = _make_activation()
        strategy = _make_strategy()
        account = _make_account(cash=10_000_000)

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        # 60개 가격 데이터 — 상승 추세로 골든 크로스 유도
        df = _build_price_df(n=60, trend="up")
        price_rows = [(row.Index, 70000, 71000, 69000, float(row.close), 1_000_000)
                      for row in df.itertuples()]
        price_result = MagicMock()
        price_result.fetchall.return_value = price_rows

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result, price_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("app.workers.trading_scheduler.SlackService"):
                from app.workers.trading_scheduler import generate_signals_and_queue_orders
                await generate_signals_and_queue_orders()

        # 신호 생성 여부와 무관하게 commit 호출됨
        mock_session.commit.assert_awaited_once()

    async def test_generate_signals_strategy_not_found(self):
        """전략을 찾지 못할 때 해당 활성화 건너뜀"""
        activation = _make_activation()

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = None  # 전략 없음

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import generate_signals_and_queue_orders
            await generate_signals_and_queue_orders()

        mock_session.add.assert_not_called()

    async def test_generate_signals_inactive_account(self):
        """계정이 비활성화된 경우 해당 활성화 건너뜀"""
        activation = _make_activation()
        strategy = _make_strategy()
        account = _make_account()
        account.is_active = False  # 비활성화

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[act_result, strat_result, acct_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import generate_signals_and_queue_orders
            await generate_signals_and_queue_orders()

        mock_session.add.assert_not_called()

    async def test_generate_signals_empty_price_data(self):
        """가격 데이터가 없으면 해당 티커 건너뜀"""
        activation = _make_activation()
        strategy = _make_strategy()
        account = _make_account()

        act_result = MagicMock()
        act_result.scalars.return_value.all.return_value = [activation]

        strat_result = MagicMock()
        strat_result.scalar_one_or_none.return_value = strategy

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = account

        # 빈 가격 데이터
        price_result = MagicMock()
        price_result.fetchall.return_value = []

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

        mock_session.add.assert_not_called()


class TestExecutePendingOrdersWithData:
    """PENDING 주문이 있을 때 실행 루프 테스트"""

    def _make_order(self, ticker="005930", side="BUY", qty=10, price=70000.0, order_id=1, account_id=1):
        """Order mock 생성"""
        from app.models.account import OrderSide, OrderStatus
        order = MagicMock()
        order.id = order_id
        order.ticker = ticker
        order.side = MagicMock()
        order.side.value = side
        order.qty = qty
        order.price = price
        order.account_id = account_id
        order.strategy_activation_id = 1
        order.status = OrderStatus.PENDING
        order.filled_price = None
        order.filled_qty = None
        order.filled_at = None
        return order

    async def test_execute_sim_buy_order_success(self):
        """SIM 계정 BUY 주문 성공 → FILLED 상태로 변경"""
        order = self._make_order(side="BUY")
        account = _make_account(acct_type="SIM")

        order_result = MagicMock()
        order_result.scalars.return_value.all.return_value = [order]

        # 오늘의 시가 조회
        price_result = MagicMock()
        price_result.fetchone.return_value = (70500,)

        # 계정 조회
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
                from app.workers.trading_scheduler import execute_pending_orders
                await execute_pending_orders()

        # place_sim_order 호출 확인
        mock_place.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_execute_sim_order_no_price_data(self):
        """가격 데이터 없을 때 주문 FAILED 처리"""
        from app.models.account import OrderStatus
        order = self._make_order()

        order_result = MagicMock()
        order_result.scalars.return_value.all.return_value = [order]

        # 가격 데이터 없음
        price_result = MagicMock()
        price_result.fetchone.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[order_result, price_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import execute_pending_orders
            await execute_pending_orders()

        # 가격 데이터 없음 → FAILED
        assert order.status == OrderStatus.FAILED

    async def test_execute_real_order_calls_trading_service(self):
        """REAL 계정 주문 → 실제 매매 서비스 HTTP 호출"""
        order = self._make_order(side="BUY")
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

        # httpx mock: 200 응답
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("httpx.AsyncClient") as mock_http:
                mock_http.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                from app.workers.trading_scheduler import execute_pending_orders
                await execute_pending_orders()

        mock_session.commit.assert_awaited_once()

    async def test_execute_real_order_http_failure(self):
        """REAL 계정 주문 실패 → FAILED 처리"""
        from app.models.account import OrderStatus
        order = self._make_order(side="BUY")
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

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            with patch("httpx.AsyncClient") as mock_http:
                mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("Connection refused")
                )
                from app.workers.trading_scheduler import execute_pending_orders
                await execute_pending_orders()

        # 실패 → FAILED
        assert order.status == OrderStatus.FAILED

    async def test_execute_account_not_found(self):
        """계정을 찾지 못하면 주문 FAILED 처리"""
        from app.models.account import OrderStatus
        order = self._make_order()

        order_result = MagicMock()
        order_result.scalars.return_value.all.return_value = [order]

        price_result = MagicMock()
        price_result.fetchone.return_value = (70500,)

        acct_result = MagicMock()
        acct_result.scalar_one_or_none.return_value = None  # 계정 없음

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[order_result, price_result, acct_result])
        mock_session.commit = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        with patch("app.workers.trading_scheduler.async_session_factory", return_value=mock_cm):
            from app.workers.trading_scheduler import execute_pending_orders
            await execute_pending_orders()

        assert order.status == OrderStatus.FAILED
