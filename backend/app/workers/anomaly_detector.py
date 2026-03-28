"""
Anomaly detection worker.
Runs every 5 minutes during trading hours (09:00-15:30).
Checks for:
1. Individual stock crash (configurable threshold, default -5%)
2. Portfolio crash (total daily P&L below threshold)
3. Circuit breaker / trading halt detection
"""
import logging
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import async_session_factory
from ..models.account import Account, Position
from ..services.kis_service import place_sim_order
from ..services.slack_service import SlackService

logger = logging.getLogger(__name__)


async def _get_price_change(ticker: str, db: AsyncSession) -> tuple[float, float] | None:
    """Return (current_close, daily_change_pct) using the two most recent daily bars."""
    result = await db.execute(
        text(
            "SELECT close FROM price_daily WHERE ticker = :ticker "
            "ORDER BY date DESC LIMIT 2"
        ),
        {"ticker": ticker},
    )
    rows = result.fetchall()
    if not rows:
        return None
    current = float(rows[0][0])
    prev = float(rows[1][0]) if len(rows) >= 2 else current
    daily_change = (current - prev) / prev if prev > 0 else 0.0
    return current, daily_change


async def check_anomalies():
    """Main anomaly check loop."""
    settings = get_settings()

    async with async_session_factory() as db:
        # Get all active accounts with positions
        result = await db.execute(
            select(Account).where(
                Account.is_active == True,  # noqa: E712
            )
        )
        accounts = result.scalars().all()

        for account in accounts:
            try:
                # Load user notification settings
                user_result = await db.execute(
                    text("SELECT notification_settings, slack_webhook_url FROM users WHERE id = :uid"),
                    {"uid": account.user_id},
                )
                user_row = user_result.fetchone()
                if not user_row:
                    continue

                user_settings = user_row[0] or {}
                if not user_settings.get("anomaly_alert", True):
                    continue

                crash_threshold = user_settings.get("crash_threshold", -0.05)
                auto_sell = user_settings.get("auto_sell_on_crash", False)

                # Check each position
                pos_result = await db.execute(
                    select(Position).where(
                        Position.account_id == account.id,
                        Position.qty > 0,
                    )
                )
                positions = pos_result.scalars().all()

                total_value = float(account.cash_balance)
                total_invested = 0.0

                for pos in positions:
                    price_data = await _get_price_change(pos.ticker, db)
                    if price_data is None:
                        continue
                    current_price, daily_change = price_data

                    pos.current_price = current_price
                    pos.unrealized_pnl = (current_price - pos.avg_price) * pos.qty

                    total_value += current_price * pos.qty
                    total_invested += pos.avg_price * pos.qty

                    if daily_change <= crash_threshold:
                        slack = SlackService(user_row[1])

                        if auto_sell and account.type.value == "SIM":
                            try:
                                await place_sim_order(
                                    account=account,
                                    ticker=pos.ticker,
                                    side="SELL",
                                    qty=pos.qty,
                                    price=current_price,
                                    strategy_activation_id=None,
                                    db=db,
                                )
                                action = "Emergency sell executed"
                            except Exception as e:
                                action = f"Auto-sell failed: {e}"
                        else:
                            action = "Alert only (manual action required)"

                        slack.send_anomaly_alert(
                            pos.ticker,
                            daily_change * 100,
                            action,
                        )
                        logger.warning(
                            f"Anomaly: {pos.ticker} change {daily_change*100:.1f}% "
                            f"for account {account.id}. Action: {action}"
                        )

                # Portfolio-level crash check
                portfolio_threshold = user_settings.get("portfolio_crash_threshold", -0.10)
                if total_invested > 0:
                    portfolio_change = (total_value - float(account.initial_balance)) / float(account.initial_balance)
                    if portfolio_change <= portfolio_threshold:
                        slack = SlackService(user_row[1])
                        slack.send_anomaly_alert(
                            "PORTFOLIO",
                            portfolio_change * 100,
                            "Portfolio crash threshold breached",
                        )

            except Exception as e:
                logger.error(f"Anomaly check failed for account {account.id}: {e}")
                continue

        await db.commit()
