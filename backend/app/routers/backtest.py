import json
import logging
from datetime import datetime, timezone

from celery import Celery
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models.backtest import BacktestRun, BacktestStatus, ValidationMode
from ..models.strategy import Strategy
from ..models.user import User
from ..schemas.backtest import (
    BacktestCompareRequest,
    BacktestRunRequest,
    BacktestRunResponse,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])
logger = logging.getLogger(__name__)


def _get_celery_app(settings: Settings) -> Celery:
    return Celery(
        "backtest_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )


async def _fetch_prices(db: AsyncSession, tickers: list[str], start_date, end_date) -> str:
    """Fetch price data from DB and return as JSON string."""
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
        rows = result.fetchall()
        for r in rows:
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


async def _fetch_benchmark(db: AsyncSession, ticker: str, start_date, end_date) -> str | None:
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
    data = [
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
    return json.dumps(data)


@router.post("/run", response_model=BacktestRunResponse, status_code=201)
async def create_backtest_run(
    req: BacktestRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    # Verify strategy ownership
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == req.strategy_id,
            Strategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Create run record
    run = BacktestRun(
        user_id=current_user.id,
        strategy_id=req.strategy_id,
        status=BacktestStatus.PENDING,
        validation_mode=ValidationMode(req.validation_type),
        validation_params=req.validation_params,
        tickers=req.tickers,
        start_date=req.start_date,
        end_date=req.end_date,
        benchmark_ticker=req.benchmark_ticker,
    )
    db.add(run)
    await db.flush()

    # Fetch price data
    prices_json = await _fetch_prices(db, req.tickers, req.start_date, req.end_date)
    benchmark_json = await _fetch_benchmark(
        db, req.benchmark_ticker, req.start_date, req.end_date
    )

    # Dispatch Celery task
    celery_app = _get_celery_app(settings)
    task = celery_app.send_task(
        "worker.tasks.run_backtest_task",
        kwargs={
            "run_id": run.id,
            "algorithm_type": strategy.algorithm_type.value,
            "params": strategy.params,
            "trade_params": strategy.trade_params,
            "prices_json": prices_json,
            "benchmark_json": benchmark_json,
            "validation_type": req.validation_type,
            "validation_params": req.validation_params,
        },
    )

    run.celery_task_id = task.id
    run.status = BacktestStatus.RUNNING
    await db.flush()

    return run


@router.get("/runs", response_model=list[BacktestRunResponse])
async def list_backtest_runs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacktestRun)
        .where(BacktestRun.user_id == current_user.id)
        .order_by(BacktestRun.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/runs/{run_id}", response_model=BacktestRunResponse)
async def get_backtest_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    result = await db.execute(
        select(BacktestRun).where(
            BacktestRun.id == run_id,
            BacktestRun.user_id == current_user.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")

    # If still running, check Celery task status
    if run.status == BacktestStatus.RUNNING and run.celery_task_id:
        celery_app = _get_celery_app(settings)
        task_result = celery_app.AsyncResult(run.celery_task_id)

        if task_result.ready():
            if task_result.successful():
                result_data = task_result.result
                run.status = BacktestStatus.DONE
                run.result_json = result_data
                run.completed_at = datetime.now(timezone.utc)
            else:
                run.status = BacktestStatus.FAILED
                run.error_message = str(task_result.info)
                run.completed_at = datetime.now(timezone.utc)
            await db.flush()

    return run


@router.post("/compare")
async def compare_strategies(
    req: BacktestCompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Run multiple strategies on the same tickers/period for comparison."""
    runs = []
    for strategy_id in req.strategy_ids:
        run_req = BacktestRunRequest(
            strategy_id=strategy_id,
            tickers=req.tickers,
            start_date=req.start_date,
            end_date=req.end_date,
            benchmark_ticker=req.benchmark_ticker,
        )
        run = await create_backtest_run(run_req, db, current_user, settings)
        runs.append(run)

    return {"runs": runs, "message": f"Started {len(runs)} comparison backtest runs"}


@router.websocket("/ws/{run_id}")
async def backtest_ws(
    websocket: WebSocket,
    run_id: int,
    settings: Settings = Depends(get_settings),
):
    """WebSocket endpoint to stream backtest progress."""
    await websocket.accept()
    celery_app = _get_celery_app(settings)

    try:
        # Find the run's Celery task ID
        async with (await __import__("contextlib").asynccontextmanager(
            lambda: get_db()
        )()) as db:
            pass
        # Simplified: poll Celery task status
        import asyncio

        while True:
            # Check all recent tasks for this run_id
            # In practice, we'd store task_id and look it up
            await websocket.send_json({"run_id": run_id, "status": "polling"})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error for run {run_id}: {e}")
