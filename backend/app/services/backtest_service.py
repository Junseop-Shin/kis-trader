import json
import logging
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.account import Account, Order
from ..models.backtest import BacktestRun, BacktestStatus, ValidationMode
from ..models.strategy import Strategy

logger = logging.getLogger(__name__)


def _get_celery_app(settings: Settings) -> Celery:
    return Celery(
        "backtest_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )


async def _fetch_prices_for_tickers(
    db: AsyncSession, tickers: list[str], start_date, end_date
) -> str:
    all_prices = []
    for ticker in tickers:
        result = await db.execute(
            text(
                "SELECT date, open, high, low, close, volume FROM price_daily "
                "WHERE ticker = :ticker AND date >= :start AND date <= :end "
                "ORDER BY date"
            ),
            {"ticker": ticker, "start": start_date, "end": end_date},
        )
        for r in result.fetchall():
            all_prices.append(
                {
                    "date": r[0].isoformat(),
                    "open": r[1],
                    "high": r[2],
                    "low": r[3],
                    "close": r[4],
                    "volume": r[5],
                }
            )
    return json.dumps(all_prices)


async def _fetch_benchmark_prices(
    db: AsyncSession, ticker: str | None, start_date, end_date
) -> str | None:
    if not ticker:
        return None
    result = await db.execute(
        text(
            "SELECT date, open, high, low, close, volume FROM price_daily "
            "WHERE ticker = :ticker AND date >= :start AND date <= :end "
            "ORDER BY date"
        ),
        {"ticker": ticker, "start": start_date, "end": end_date},
    )
    rows = result.fetchall()
    if not rows:
        return None
    return json.dumps(
        [
            {
                "date": r[0].isoformat(),
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
            }
            for r in rows
        ]
    )


async def run_counterfactual(
    account_id: int,
    strategy_ids: list[int],
    user_id: int,
    db: AsyncSession,
    settings: Settings,
) -> dict:
    """
    For an account's actual trading history period, run N strategies and compare.
    Returns run IDs for comparison overlay.
    """
    # Verify account ownership
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise ValueError("Account not found")

    # Get the account's trading period from orders
    result = await db.execute(
        text(
            "SELECT MIN(created_at)::date, MAX(created_at)::date "
            "FROM orders WHERE account_id = :aid"
        ),
        {"aid": account_id},
    )
    row = result.fetchone()
    if not row or row[0] is None:
        raise ValueError("No trading history found for this account")

    start_date = row[0]
    end_date = row[1]

    # Get tickers the account actually traded
    result = await db.execute(
        text(
            "SELECT DISTINCT ticker FROM orders WHERE account_id = :aid"
        ),
        {"aid": account_id},
    )
    tickers = [r[0] for r in result.fetchall()]

    if not tickers:
        raise ValueError("No tickers found in account trading history")

    # Fetch price data
    prices_json = await _fetch_prices_for_tickers(db, tickers, start_date, end_date)
    benchmark_json = await _fetch_benchmark_prices(db, "069500", start_date, end_date)

    celery_app = _get_celery_app(settings)
    runs = []

    for strategy_id in strategy_ids:
        # Verify strategy ownership
        result = await db.execute(
            select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user_id)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            continue

        run = BacktestRun(
            user_id=user_id,
            strategy_id=strategy_id,
            status=BacktestStatus.PENDING,
            validation_mode=ValidationMode.SIMPLE,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            benchmark_ticker="069500",
        )
        db.add(run)
        await db.flush()

        task = celery_app.send_task(
            "worker.tasks.run_backtest_task",
            kwargs={
                "run_id": run.id,
                "algorithm_type": strategy.algorithm_type.value,
                "params": strategy.params,
                "trade_params": strategy.trade_params,
                "prices_json": prices_json,
                "benchmark_json": benchmark_json,
                "validation_type": "SIMPLE",
            },
        )
        run.celery_task_id = task.id
        run.status = BacktestStatus.RUNNING
        await db.flush()

        runs.append(
            {
                "run_id": run.id,
                "strategy_id": strategy_id,
                "strategy_name": strategy.name,
                "celery_task_id": task.id,
            }
        )

    # Also generate the account's actual equity curve for comparison
    result = await db.execute(
        text(
            "SELECT date, total_value FROM account_daily "
            "WHERE account_id = :aid ORDER BY date"
        ),
        {"aid": account_id},
    )
    actual_equity = [
        {"date": r[0].isoformat(), "portfolio_value": float(r[1])}
        for r in result.fetchall()
    ]

    return {
        "account_id": account_id,
        "period": f"{start_date} ~ {end_date}",
        "tickers": tickers,
        "counterfactual_runs": runs,
        "actual_equity_curve": actual_equity,
    }
