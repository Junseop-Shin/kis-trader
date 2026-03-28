"""
Risk management for real-money trading.
All orders must pass these checks before execution.
"""
import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Default risk limits
DEFAULT_DAILY_LOSS_LIMIT = 500_000  # 50만 KRW max daily loss
DEFAULT_MAX_POSITION_SIZE_PCT = 0.30  # 30% of portfolio in single stock
DEFAULT_MAX_POSITIONS = 10  # Max simultaneous positions
DEFAULT_SINGLE_ORDER_LIMIT = 5_000_000  # 500만 KRW max per order


class RiskManager:
    def __init__(
        self,
        daily_loss_limit: int = DEFAULT_DAILY_LOSS_LIMIT,
        max_position_size_pct: float = DEFAULT_MAX_POSITION_SIZE_PCT,
        max_positions: int = DEFAULT_MAX_POSITIONS,
        single_order_limit: int = DEFAULT_SINGLE_ORDER_LIMIT,
    ):
        self.daily_loss_limit = daily_loss_limit
        self.max_position_size_pct = max_position_size_pct
        self.max_positions = max_positions
        self.single_order_limit = single_order_limit

    def check_order(
        self,
        side: str,
        qty: int,
        price: float,
        cash_balance: int,
        total_portfolio_value: int,
        current_positions_count: int,
        existing_position_value: float = 0,
    ) -> tuple[bool, str]:
        """
        Returns (allowed, reason) based on risk rules.
        """
        order_value = qty * price

        # Single order amount limit
        if order_value > self.single_order_limit:
            return False, (
                f"Order value {order_value:,.0f} exceeds single order limit "
                f"of {self.single_order_limit:,.0f} KRW"
            )

        if side == "BUY":
            # Sufficient cash check
            if order_value > cash_balance:
                return False, (
                    f"Insufficient cash. Order: {order_value:,.0f}, "
                    f"Available: {cash_balance:,.0f} KRW"
                )

            # Max position size check
            if total_portfolio_value > 0:
                new_position_value = existing_position_value + order_value
                position_pct = new_position_value / total_portfolio_value
                if position_pct > self.max_position_size_pct:
                    return False, (
                        f"Position would be {position_pct*100:.1f}% of portfolio, "
                        f"exceeding {self.max_position_size_pct*100:.0f}% limit"
                    )

            # Max simultaneous positions
            if existing_position_value == 0 and current_positions_count >= self.max_positions:
                return False, (
                    f"Already holding {current_positions_count} positions, "
                    f"max is {self.max_positions}"
                )

        return True, "OK"

    async def check_daily_loss(self, account_id: int, db: AsyncSession) -> tuple[bool, float]:
        """
        Check if daily loss exceeds limit.
        Returns (is_allowed, current_daily_pnl).
        """
        today = date.today()
        result = await db.execute(
            text(
                "SELECT COALESCE(SUM(pnl), 0) FROM orders "
                "WHERE account_id = :aid AND DATE(filled_at) = :today AND status = 'FILLED'"
            ),
            {"aid": account_id, "today": today},
        )
        daily_pnl = float(result.scalar() or 0)

        if daily_pnl < -self.daily_loss_limit:
            return False, daily_pnl

        return True, daily_pnl
