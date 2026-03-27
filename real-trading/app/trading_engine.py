"""
Trading engine that coordinates between KIS client and risk manager.
"""
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .kis_client import KISClient, decrypt_value
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/kistrader")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

risk_manager = RiskManager()


async def _get_kis_client(account_id: int, db: AsyncSession) -> KISClient:
    """Build KIS client from encrypted credentials in DB."""
    result = await db.execute(
        text(
            "SELECT kis_account_no, kis_app_key, kis_app_secret, kis_access_token "
            "FROM accounts WHERE id = :aid AND type = 'REAL'"
        ),
        {"aid": account_id},
    )
    row = result.fetchone()
    if not row:
        raise ValueError(f"Real account {account_id} not found")

    return KISClient(
        app_key=decrypt_value(row[1]),
        app_secret=decrypt_value(row[2]),
        account_no=row[0],
        access_token=decrypt_value(row[3]) if row[3] else None,
    )


async def execute_real_order(
    account_id: int,
    ticker: str,
    side: str,
    qty: int,
    price: int,
) -> dict:
    """Execute a real order with risk checks."""
    async with session_factory() as db:
        # Get account info
        result = await db.execute(
            text(
                "SELECT cash_balance, initial_balance FROM accounts WHERE id = :aid"
            ),
            {"aid": account_id},
        )
        acct_row = result.fetchone()
        if not acct_row:
            raise ValueError("Account not found")

        cash_balance = acct_row[0]
        total_value = acct_row[1]

        # Count positions
        pos_result = await db.execute(
            text(
                "SELECT COUNT(*), COALESCE(SUM(CASE WHEN ticker = :ticker THEN qty * avg_price ELSE 0 END), 0) "
                "FROM positions WHERE account_id = :aid AND qty > 0"
            ),
            {"aid": account_id, "ticker": ticker},
        )
        pos_row = pos_result.fetchone()
        positions_count = pos_row[0] if pos_row else 0
        existing_value = float(pos_row[1]) if pos_row else 0

        # Risk check
        allowed, reason = risk_manager.check_order(
            side=side,
            qty=qty,
            price=float(price),
            cash_balance=cash_balance,
            total_portfolio_value=total_value,
            current_positions_count=positions_count,
            existing_position_value=existing_value,
        )
        if not allowed:
            raise ValueError(f"Risk check failed: {reason}")

        # Daily loss check
        daily_ok, daily_pnl = await risk_manager.check_daily_loss(account_id, db)
        if not daily_ok:
            raise ValueError(f"Daily loss limit exceeded: {daily_pnl:,.0f} KRW")

        # Execute via KIS
        kis = await _get_kis_client(account_id, db)
        order_result = await kis.place_order(ticker, side, qty, price)

        # Record order in DB
        await db.execute(
            text(
                "INSERT INTO orders (account_id, ticker, side, qty, price, "
                "filled_qty, filled_price, status, kis_order_no, filled_at, created_at) "
                "VALUES (:aid, :ticker, :side, :qty, :price, :qty, :price, "
                "'FILLED', :order_no, :now, :now)"
            ),
            {
                "aid": account_id,
                "ticker": ticker,
                "side": side,
                "qty": qty,
                "price": price,
                "order_no": order_result.get("order_no", ""),
                "now": datetime.now(timezone.utc),
            },
        )
        await db.commit()

        return {
            "status": "FILLED",
            "order_no": order_result.get("order_no", ""),
            "ticker": ticker,
            "side": side,
            "qty": qty,
            "price": price,
        }


async def get_account_balance(account_id: int) -> dict:
    """Get real account balance via KIS API."""
    async with session_factory() as db:
        kis = await _get_kis_client(account_id, db)
        return await kis.get_balance()


async def get_account_positions(account_id: int) -> list[dict]:
    """Get real account positions via KIS API."""
    async with session_factory() as db:
        kis = await _get_kis_client(account_id, db)
        return await kis.get_positions()
