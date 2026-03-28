"""
매매 흐름 통합 테스트
시뮬레이션 전략 활성화 -> 신호 생성 -> T+1 주문 -> 포트폴리오 반영
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.models.account import Account, AccountType, Position, Order, OrderSide, OrderStatus
from app.models.strategy import Strategy, AlgorithmType
from app.models.trading import StrategyActivation, ActivationStatus
from tests.conftest import user_auth_header


class TestTradingFlow:
    """매매 전체 흐름 통합 테스트"""

    async def test_activate_strategy_on_sim_account(
        self, client, test_user, test_account, test_strategy, user_token
    ):
        """시뮬 계정에 전략 활성화"""
        r = await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": test_account.id,
                "tickers": ["005930", "000660"],
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "ACTIVE"
        assert data["tickers"] == ["005930", "000660"]

    async def test_activate_duplicate_rejected(
        self, client, test_user, test_account, test_strategy, user_token
    ):
        """동일 전략을 같은 계정에 중복 활성화하면 400 에러"""
        payload = {
            "strategy_id": test_strategy.id,
            "account_id": test_account.id,
            "tickers": ["005930"],
        }
        r = await client.post(
            "/trading/activate",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 201

        # 중복 활성화 시도
        r = await client.post(
            "/trading/activate",
            json=payload,
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 400

    async def test_activate_with_nonowned_strategy(
        self, client, test_user, test_account, user_token
    ):
        """소유하지 않은 전략으로 활성화 시도 시 404"""
        r = await client.post(
            "/trading/activate",
            json={
                "strategy_id": 99999,
                "account_id": test_account.id,
                "tickers": ["005930"],
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_activate_with_nonowned_account(
        self, client, test_user, test_strategy, user_token
    ):
        """소유하지 않은 계정으로 활성화 시도 시 404"""
        r = await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": 99999,
                "tickers": ["005930"],
            },
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_deactivate_strategy(
        self, client, db_session, test_user, test_account, test_strategy, user_token
    ):
        """활성화된 전략 비활성화"""
        # 먼저 활성화
        r = await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": test_account.id,
                "tickers": ["005930"],
            },
            headers=user_auth_header(user_token),
        )
        activation_id = r.json()["id"]

        # 비활성화
        r = await client.post(
            "/trading/deactivate",
            json={"activation_id": activation_id},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 200
        assert r.json()["message"] == "Strategy deactivated"

    async def test_deactivate_nonexistent_activation(
        self, client, test_user, user_token
    ):
        """존재하지 않는 활성화 비활성화 시 404"""
        r = await client.post(
            "/trading/deactivate",
            json={"activation_id": 99999},
            headers=user_auth_header(user_token),
        )
        assert r.status_code == 404

    async def test_list_active_strategies(
        self, client, db_session, test_user, test_account, test_strategy, user_token
    ):
        """활성 전략 목록 조회"""
        # 활성화
        await client.post(
            "/trading/activate",
            json={
                "strategy_id": test_strategy.id,
                "account_id": test_account.id,
                "tickers": ["005930"],
            },
            headers=user_auth_header(user_token),
        )

        r = await client.get("/trading/active", headers=user_auth_header(user_token))
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        assert items[0]["status"] == "ACTIVE"


class TestSimOrderFlow:
    """시뮬레이션 주문 서비스 테스트"""

    async def test_sim_buy_order(self, db_session, test_account):
        """시뮬 매수 주문 시 잔고 차감 및 포지션 생성"""
        from app.services.kis_service import place_sim_order

        order = await place_sim_order(
            account=test_account,
            ticker="005930",
            side="BUY",
            qty=10,
            price=70000,
            strategy_activation_id=None,
            db=db_session,
        )
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 10

        # 잔고 차감 확인
        assert test_account.cash_balance < 10_000_000

    async def test_sim_buy_then_sell(self, db_session, test_account):
        """시뮬 매수 후 매도 시 수익/손실 계산 및 포지션 해제"""
        from app.services.kis_service import place_sim_order

        # 매수
        await place_sim_order(
            account=test_account,
            ticker="005930",
            side="BUY",
            qty=10,
            price=70000,
            strategy_activation_id=None,
            db=db_session,
        )
        balance_after_buy = test_account.cash_balance

        # 매도 (이익)
        sell_order = await place_sim_order(
            account=test_account,
            ticker="005930",
            side="SELL",
            qty=10,
            price=75000,
            strategy_activation_id=None,
            db=db_session,
        )
        assert sell_order.pnl is not None
        assert sell_order.pnl > 0  # 75000 - 70000 = 수익

        # 잔고 증가 확인
        assert test_account.cash_balance > balance_after_buy

    async def test_sim_buy_insufficient_balance(self, db_session, test_account):
        """잔고 부족 시 매수 실패"""
        from app.services.kis_service import place_sim_order

        with pytest.raises(ValueError, match="Insufficient balance"):
            await place_sim_order(
                account=test_account,
                ticker="005930",
                side="BUY",
                qty=10000,
                price=70000,
                strategy_activation_id=None,
                db=db_session,
            )

    async def test_sim_sell_without_position(self, db_session, test_account):
        """보유하지 않은 종목 매도 시 실패"""
        from app.services.kis_service import place_sim_order

        with pytest.raises(ValueError, match="Insufficient position"):
            await place_sim_order(
                account=test_account,
                ticker="005930",
                side="SELL",
                qty=10,
                price=70000,
                strategy_activation_id=None,
                db=db_session,
            )

    async def test_sim_partial_sell(self, db_session, test_account):
        """보유 수량 중 일부만 매도"""
        from app.services.kis_service import place_sim_order

        # 20주 매수
        await place_sim_order(
            account=test_account,
            ticker="005930",
            side="BUY",
            qty=20,
            price=70000,
            strategy_activation_id=None,
            db=db_session,
        )

        # 10주만 매도
        order = await place_sim_order(
            account=test_account,
            ticker="005930",
            side="SELL",
            qty=10,
            price=72000,
            strategy_activation_id=None,
            db=db_session,
        )
        assert order.filled_qty == 10

        # 나머지 10주 포지션 확인
        from sqlalchemy import select
        from app.models.account import Position
        result = await db_session.execute(
            select(Position).where(
                Position.account_id == test_account.id,
                Position.ticker == "005930",
            )
        )
        pos = result.scalar_one_or_none()
        assert pos is not None
        assert pos.qty == 10
