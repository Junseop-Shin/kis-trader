import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.account import Account, AccountType, Position, Order, OrderSide, OrderStatus

logger = logging.getLogger(__name__)


async def place_sim_order(
    account: Account,
    ticker: str,
    side: str,
    qty: int,
    price: float,
    strategy_activation_id: int | None,
    db: AsyncSession,
) -> Order:
    """
    Paper trading: execute order against SIM account balance.
    No real KIS API call needed for simulation.
    """
    commission_pct = 0.00015
    tax_pct = 0.002 if side == "SELL" else 0

    if side == "BUY":
        # Lock the account row to prevent concurrent double-spend
        locked = await db.execute(
            select(type(account)).where(type(account).id == account.id).with_for_update()
        )
        account = locked.scalar_one()

        total_cost = qty * price * (1 + commission_pct)
        if total_cost > account.cash_balance:
            raise ValueError(f"Insufficient balance. Need {total_cost:,.0f}, have {account.cash_balance:,.0f}")

        account.cash_balance -= int(total_cost)

        # Update or create position
        result = await db.execute(
            select(Position).where(
                Position.account_id == account.id,
                Position.ticker == ticker,
            )
        )
        position = result.scalar_one_or_none()

        if position:
            total_qty = position.qty + qty
            position.avg_price = (
                (position.avg_price * position.qty + price * qty) / total_qty
            )
            position.qty = total_qty
        else:
            position = Position(
                account_id=account.id,
                ticker=ticker,
                qty=qty,
                avg_price=price,
                current_price=price,
            )
            db.add(position)

    elif side == "SELL":
        result = await db.execute(
            select(Position).where(
                Position.account_id == account.id,
                Position.ticker == ticker,
            )
        )
        position = result.scalar_one_or_none()

        if not position or position.qty < qty:
            raise ValueError(f"Insufficient position for {ticker}. Have {position.qty if position else 0}")

        proceeds = qty * price * (1 - commission_pct - tax_pct)
        pnl = (price - position.avg_price) * qty

        account.cash_balance += int(proceeds)
        position.qty -= qty

        if position.qty == 0:
            await db.delete(position)

    order = Order(
        account_id=account.id,
        strategy_activation_id=strategy_activation_id,
        ticker=ticker,
        side=OrderSide(side),
        qty=qty,
        price=price,
        filled_qty=qty,
        filled_price=price,
        status=OrderStatus.FILLED,
        pnl=pnl if side == "SELL" else None,
        filled_at=datetime.now(timezone.utc),
    )
    db.add(order)
    await db.flush()

    return order


async def sync_sim_account(account: Account, db: AsyncSession) -> None:
    """Update SIM account positions with current prices from price_daily."""
    result = await db.execute(
        select(Position).where(
            Position.account_id == account.id,
            Position.qty > 0,
        )
    )
    positions = result.scalars().all()

    for pos in positions:
        price_result = await db.execute(
            text(
                "SELECT close FROM price_daily WHERE ticker = :ticker "
                "ORDER BY date DESC LIMIT 1"
            ),
            {"ticker": pos.ticker},
        )
        row = price_result.fetchone()
        if row:
            pos.current_price = float(row[0])
            pos.unrealized_pnl = (pos.current_price - pos.avg_price) * pos.qty

    await db.flush()
