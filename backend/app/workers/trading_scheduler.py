"""
T+1 Trading Scheduler.

Daily at 15:35 (after market close):
  - Find all active strategy activations
  - Fetch today's price data and generate signals
  - Create pending orders for T+1 execution

Daily at 09:05 (market open):
  - Execute all pending orders at current open price
  - Update positions and account balance
  - Send Slack notifications
"""
import json
import logging
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import async_session_factory
from ..models.account import Account, Order, OrderSide, OrderStatus, Position
from ..models.strategy import Strategy
from ..models.trading import StrategyActivation, ActivationStatus
from ..services.kis_service import place_sim_order
from ..services.slack_service import SlackService

logger = logging.getLogger(__name__)


# Algorithm imports (inline to avoid circular dependency)
ALGORITHM_MAP = {
    "MA_CROSS": "MACrossAlgorithm",
    "RSI": "RSIAlgorithm",
    "MACD": "MACDAlgorithm",
    "BOLLINGER": "BollingerAlgorithm",
    "MOMENTUM": "MomentumAlgorithm",
    "STOCHASTIC": "StochasticAlgorithm",
    "MEAN_REVERT": "MeanRevertAlgorithm",
}


def _get_algo_class(algorithm_type: str):
    """Lazily import algorithm classes to avoid heavy imports at module level."""
    import importlib

    module_map = {
        "MA_CROSS": ("backtest-worker.worker.algorithms.ma_cross", "MACrossAlgorithm"),
        "RSI": ("backtest-worker.worker.algorithms.rsi", "RSIAlgorithm"),
        "MACD": ("backtest-worker.worker.algorithms.macd", "MACDAlgorithm"),
        "BOLLINGER": ("backtest-worker.worker.algorithms.bollinger", "BollingerAlgorithm"),
        "MOMENTUM": ("backtest-worker.worker.algorithms.momentum", "MomentumAlgorithm"),
        "STOCHASTIC": ("backtest-worker.worker.algorithms.stochastic", "StochasticAlgorithm"),
        "MEAN_REVERT": ("backtest-worker.worker.algorithms.mean_revert", "MeanRevertAlgorithm"),
    }

    # For the backend, we implement signal generation inline
    # since the worker algorithms may not be importable from here
    return None


async def _get_recent_prices(db: AsyncSession, ticker: str, lookback: int = 60) -> pd.DataFrame:
    """Fetch recent daily prices for signal generation."""
    result = await db.execute(
        text(
            "SELECT date, open, high, low, close, volume FROM price_daily "
            "WHERE ticker = :ticker ORDER BY date DESC LIMIT :limit"
        ),
        {"ticker": ticker, "limit": lookback},
    )
    rows = result.fetchall()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def _generate_signal_simple(df: pd.DataFrame, algo_type: str, params: dict) -> int:
    """
    Simplified signal generation for the scheduler.
    Returns: 1 (BUY), -1 (SELL), 0 (HOLD)
    """
    if len(df) < 30:
        return 0

    close = df["close"].astype(float)

    if algo_type == "MA_CROSS":
        short = params.get("short_period", 5)
        long_ = params.get("long_period", 20)
        ma_type = params.get("ma_type", "SMA")
        if ma_type == "EMA":
            short_ma = close.ewm(span=short, adjust=False).mean()
            long_ma = close.ewm(span=long_, adjust=False).mean()
        else:
            short_ma = close.rolling(short).mean()
            long_ma = close.rolling(long_).mean()

        if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
            return 1
        if short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
            return -1

    elif algo_type == "RSI":
        import pandas_ta as ta
        period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        rsi = ta.rsi(close, length=period)
        if rsi is not None and len(rsi) >= 2:
            if rsi.iloc[-2] < oversold and rsi.iloc[-1] >= oversold:
                return 1
            if rsi.iloc[-2] < overbought and rsi.iloc[-1] >= overbought:
                return -1

    elif algo_type == "MACD":
        import pandas_ta as ta
        fast = params.get("fast", 12)
        slow = params.get("slow", 26)
        signal_p = params.get("signal", 9)
        macd_df = ta.macd(close, fast=fast, slow=slow, signal=signal_p)
        if macd_df is not None and len(macd_df) >= 2:
            macd_line = macd_df.iloc[:, 0]
            signal_line = macd_df.iloc[:, 2]
            if macd_line.iloc[-2] <= signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]:
                return 1
            if macd_line.iloc[-2] >= signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]:
                return -1

    elif algo_type == "BOLLINGER":
        import pandas_ta as ta
        period = params.get("period", 20)
        std_dev = params.get("std_dev", 2.0)
        mode = params.get("mode", "reversion")
        bb = ta.bbands(close, length=period, std=std_dev)
        if bb is not None and len(bb) >= 2:
            lower = bb.iloc[:, 0]
            upper = bb.iloc[:, 2]
            if mode == "reversion":
                if close.iloc[-1] < lower.iloc[-1]:
                    return 1
                if close.iloc[-1] > upper.iloc[-1]:
                    return -1

    return 0


async def generate_signals_and_queue_orders():
    """
    Run at 15:35 daily (after market close).
    Generate signals and create PENDING orders for T+1.
    """
    settings = get_settings()
    logger.info("Running signal generation for active strategies...")

    async with async_session_factory() as db:
        result = await db.execute(
            select(StrategyActivation)
            .where(StrategyActivation.status == ActivationStatus.ACTIVE)
        )
        activations = result.scalars().all()

        for activation in activations:
            try:
                # Load strategy
                strat_result = await db.execute(
                    select(Strategy).where(Strategy.id == activation.strategy_id)
                )
                strategy = strat_result.scalar_one_or_none()
                if not strategy:
                    continue

                # Load account
                acct_result = await db.execute(
                    select(Account).where(Account.id == activation.account_id)
                )
                account = acct_result.scalar_one_or_none()
                if not account or not account.is_active:
                    continue

                for ticker in activation.tickers:
                    df = await _get_recent_prices(db, ticker)
                    if df.empty:
                        continue

                    signal = _generate_signal_simple(
                        df, strategy.algorithm_type.value, strategy.params
                    )

                    if signal == 0:
                        continue

                    # Determine qty and price
                    current_price = float(df["close"].iloc[-1])
                    trade_params = strategy.trade_params
                    position_size_pct = trade_params.get("position_size_pct", 0.1)

                    if signal == 1:
                        invest = account.cash_balance * position_size_pct
                        qty = int(invest / current_price)
                        if qty <= 0:
                            continue
                    elif signal == -1:
                        pos_result = await db.execute(
                            select(Position).where(
                                Position.account_id == account.id,
                                Position.ticker == ticker,
                            )
                        )
                        pos = pos_result.scalar_one_or_none()
                        if not pos or pos.qty <= 0:
                            continue
                        qty = pos.qty
                    else:
                        continue

                    # Create pending order
                    order = Order(
                        account_id=account.id,
                        strategy_activation_id=activation.id,
                        ticker=ticker,
                        side=OrderSide.BUY if signal == 1 else OrderSide.SELL,
                        qty=qty,
                        price=current_price,
                        status=OrderStatus.PENDING,
                    )
                    db.add(order)

                    activation.last_signal_date = date.today().isoformat()
                    activation.last_signal_action = "BUY" if signal == 1 else "SELL"

                    # Slack notification
                    if account.user_id:
                        slack = SlackService()
                        slack.send_trade_signal(ticker, "BUY" if signal == 1 else "SELL", current_price, strategy.name)

                    logger.info(
                        f"Queued {'BUY' if signal == 1 else 'SELL'} order: "
                        f"{ticker} x{qty} @ {current_price:,.0f} for account {account.id}"
                    )

            except Exception as e:
                logger.error(f"Signal generation failed for activation {activation.id}: {e}")
                continue

        await db.commit()

    logger.info("Signal generation complete")


async def execute_pending_orders():
    """
    Run at 09:05 daily (market open).
    Execute all PENDING orders at today's open price.
    For SIM: update balance directly.
    For REAL: call real-trading service.
    """
    settings = get_settings()
    logger.info("Executing pending orders...")

    async with async_session_factory() as db:
        result = await db.execute(
            select(Order).where(Order.status == OrderStatus.PENDING)
        )
        pending_orders = result.scalars().all()

        for order in pending_orders:
            try:
                # Get today's open price
                price_result = await db.execute(
                    text(
                        "SELECT open FROM price_daily WHERE ticker = :ticker "
                        "ORDER BY date DESC LIMIT 1"
                    ),
                    {"ticker": order.ticker},
                )
                price_row = price_result.fetchone()

                if not price_row:
                    order.status = OrderStatus.FAILED
                    continue

                execution_price = float(price_row[0])

                # Load account
                acct_result = await db.execute(
                    select(Account).where(Account.id == order.account_id)
                )
                account = acct_result.scalar_one_or_none()
                if not account:
                    order.status = OrderStatus.FAILED
                    continue

                if account.type.value == "SIM":
                    try:
                        await place_sim_order(
                            account=account,
                            ticker=order.ticker,
                            side=order.side.value,
                            qty=order.qty,
                            price=execution_price,
                            strategy_activation_id=order.strategy_activation_id,
                            db=db,
                        )
                        order.status = OrderStatus.FILLED
                        order.filled_price = execution_price
                        order.filled_qty = order.qty
                        order.filled_at = datetime.now(timezone.utc)
                    except ValueError as e:
                        order.status = OrderStatus.FAILED
                        logger.warning(f"SIM order failed: {e}")

                elif account.type.value == "REAL":
                    # Call real-trading service
                    import httpx

                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.post(
                                f"{settings.REAL_TRADING_URL}/real/order",
                                json={
                                    "account_id": account.id,
                                    "ticker": order.ticker,
                                    "side": order.side.value,
                                    "qty": order.qty,
                                    "price": execution_price,
                                },
                                timeout=30,
                            )
                            if resp.status_code == 200:
                                order.status = OrderStatus.FILLED
                                order.filled_price = execution_price
                                order.filled_qty = order.qty
                                order.filled_at = datetime.now(timezone.utc)
                            else:
                                order.status = OrderStatus.FAILED
                    except Exception as e:
                        order.status = OrderStatus.FAILED
                        logger.error(f"Real trading order failed: {e}")

            except Exception as e:
                order.status = OrderStatus.FAILED
                logger.error(f"Order execution failed for order {order.id}: {e}")

        await db.commit()

    logger.info("Pending order execution complete")


async def send_daily_reports():
    """Send daily performance report to all users via Slack."""
    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT a.id, a.user_id, a.cash_balance, "
                "COALESCE(SUM(p.qty * p.current_price), 0) as stock_value, "
                "COUNT(p.id) as position_count "
                "FROM accounts a "
                "LEFT JOIN positions p ON p.account_id = a.id AND p.qty > 0 "
                "WHERE a.is_active = true "
                "GROUP BY a.id"
            )
        )
        rows = result.fetchall()

        for row in rows:
            account_id, user_id, cash, stock_value, pos_count = row
            total = cash + int(stock_value)

            # Count active strategies
            act_result = await db.execute(
                text(
                    "SELECT COUNT(*) FROM strategy_activations "
                    "WHERE account_id = :aid AND status = 'ACTIVE'"
                ),
                {"aid": account_id},
            )
            active_count = act_result.scalar() or 0

            summary = {
                "daily_pnl": 0,  # Would need yesterday's total for comparison
                "total_value": total,
                "position_count": pos_count,
                "active_strategies": active_count,
            }

            slack = SlackService()
            slack.send_daily_report(summary)


async def send_weekly_reports():
    """Send weekly performance reports."""
    slack = SlackService()
    slack.send_weekly_report({"weekly_return": 0, "total_value": 0, "trades_count": 0})
