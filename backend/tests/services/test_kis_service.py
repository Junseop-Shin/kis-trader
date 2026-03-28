import pytest
from datetime import datetime, timezone

from app.models.account import Account, AccountType, Position, Order, OrderSide, OrderStatus
from app.services.kis_service import place_sim_order, sync_sim_account


class TestPlaceSimOrder:
    async def test_buy_order_success(self, db_session, test_account):
        order = await place_sim_order(
            account=test_account,
            ticker="005930",
            side="BUY",
            qty=10,
            price=70000.0,
            strategy_activation_id=None,
            db=db_session,
        )
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 10
        assert test_account.cash_balance < 10_000_000

    async def test_buy_creates_position(self, db_session, test_account):
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=10, price=70000.0, strategy_activation_id=None, db=db_session,
        )
        from sqlalchemy import select
        result = await db_session.execute(
            select(Position).where(
                Position.account_id == test_account.id,
                Position.ticker == "005930",
            )
        )
        pos = result.scalar_one_or_none()
        assert pos is not None
        assert pos.qty == 10
        assert pos.avg_price == 70000.0

    async def test_buy_adds_to_existing_position(self, db_session, test_account):
        # First buy
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=10, price=70000.0, strategy_activation_id=None, db=db_session,
        )
        # Second buy at different price
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=10, price=80000.0, strategy_activation_id=None, db=db_session,
        )
        from sqlalchemy import select
        result = await db_session.execute(
            select(Position).where(
                Position.account_id == test_account.id,
                Position.ticker == "005930",
            )
        )
        pos = result.scalar_one()
        assert pos.qty == 20
        assert pos.avg_price == 75000.0  # (70000*10 + 80000*10) / 20

    async def test_buy_insufficient_balance_raises(self, db_session, test_account):
        with pytest.raises(ValueError, match="Insufficient balance"):
            await place_sim_order(
                account=test_account, ticker="005930", side="BUY",
                qty=1000, price=70000.0, strategy_activation_id=None, db=db_session,
            )

    async def test_sell_order_success(self, db_session, test_account):
        # First buy
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=10, price=70000.0, strategy_activation_id=None, db=db_session,
        )
        balance_after_buy = test_account.cash_balance
        # Then sell
        order = await place_sim_order(
            account=test_account, ticker="005930", side="SELL",
            qty=10, price=75000.0, strategy_activation_id=None, db=db_session,
        )
        assert order.side == OrderSide.SELL
        assert order.pnl is not None
        assert test_account.cash_balance > balance_after_buy

    async def test_sell_insufficient_position_raises(self, db_session, test_account):
        with pytest.raises(ValueError, match="Insufficient position"):
            await place_sim_order(
                account=test_account, ticker="005930", side="SELL",
                qty=10, price=70000.0, strategy_activation_id=None, db=db_session,
            )

    async def test_sell_more_than_held_raises(self, db_session, test_account):
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=5, price=70000.0, strategy_activation_id=None, db=db_session,
        )
        with pytest.raises(ValueError, match="Insufficient position"):
            await place_sim_order(
                account=test_account, ticker="005930", side="SELL",
                qty=10, price=70000.0, strategy_activation_id=None, db=db_session,
            )

    async def test_sell_all_deletes_position(self, db_session, test_account):
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=10, price=70000.0, strategy_activation_id=None, db=db_session,
        )
        await place_sim_order(
            account=test_account, ticker="005930", side="SELL",
            qty=10, price=75000.0, strategy_activation_id=None, db=db_session,
        )
        from sqlalchemy import select
        result = await db_session.execute(
            select(Position).where(
                Position.account_id == test_account.id,
                Position.ticker == "005930",
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_commission_applied_on_buy(self, db_session, test_account):
        initial = test_account.cash_balance
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=100, price=1000.0, strategy_activation_id=None, db=db_session,
        )
        # cost = 100 * 1000 * (1 + 0.00015) = 100015
        expected_cost = 100 * 1000 * (1 + 0.00015)
        assert test_account.cash_balance == initial - int(expected_cost)

    async def test_tax_applied_on_sell(self, db_session, test_account):
        await place_sim_order(
            account=test_account, ticker="005930", side="BUY",
            qty=100, price=1000.0, strategy_activation_id=None, db=db_session,
        )
        balance_before_sell = test_account.cash_balance
        await place_sim_order(
            account=test_account, ticker="005930", side="SELL",
            qty=100, price=1000.0, strategy_activation_id=None, db=db_session,
        )
        # proceeds = 100 * 1000 * (1 - 0.00015 - 0.002)
        expected_proceeds = 100 * 1000 * (1 - 0.00015 - 0.002)
        assert test_account.cash_balance == balance_before_sell + int(expected_proceeds)
