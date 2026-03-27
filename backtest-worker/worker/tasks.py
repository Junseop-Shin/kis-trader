import itertools
import json
import logging

import pandas as pd

from .celery_app import app
from .algorithms import ALGORITHM_MAP

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, name="worker.tasks.run_backtest_task")
def run_backtest_task(
    self,
    run_id: int,
    algorithm_type: str,
    params: dict,
    trade_params: dict,
    prices_json: str,
    benchmark_json: str | None = None,
    validation_type: str = "SIMPLE",
    validation_params: dict | None = None,
):
    """Main backtest task executed on Mac Mini Celery worker."""
    try:
        self.update_state(state="STARTED", meta={"progress": 0, "run_id": run_id})

        AlgoClass = ALGORITHM_MAP.get(algorithm_type)
        if not AlgoClass:
            raise ValueError(f"Unknown algorithm: {algorithm_type}")

        algo = AlgoClass(params, trade_params)

        prices = pd.DataFrame(json.loads(prices_json))
        prices["date"] = pd.to_datetime(prices["date"])
        prices = prices.set_index("date").sort_index()

        benchmark = None
        if benchmark_json:
            benchmark = pd.DataFrame(json.loads(benchmark_json))
            benchmark["date"] = pd.to_datetime(benchmark["date"])
            benchmark = benchmark.set_index("date").sort_index()

        self.update_state(state="PROGRESS", meta={"progress": 20, "run_id": run_id})

        if validation_type == "WALK_FORWARD":
            results = _run_walk_forward(algo, prices, benchmark, validation_params or {})
        elif validation_type == "OPTIMIZE":
            results = _run_optimize(
                AlgoClass, params, trade_params, prices, benchmark, validation_params or {}
            )
            self.update_state(state="PROGRESS", meta={"progress": 80, "run_id": run_id})
        else:
            trades, equity_curve, metrics = algo.run(prices, benchmark)
            results = {
                "trades": [t.__dict__ for t in trades],
                "equity_curve": equity_curve,
                "metrics": metrics.__dict__,
            }

        self.update_state(state="PROGRESS", meta={"progress": 90, "run_id": run_id})
        return {"run_id": run_id, "status": "DONE", **results}

    except Exception as exc:
        logger.exception(f"Backtest task failed for run_id={run_id}")
        self.update_state(state="FAILURE", meta={"error": str(exc), "run_id": run_id})
        raise self.retry(exc=exc, countdown=5)


def _run_walk_forward(algo, prices, benchmark, params):
    """Walk-forward validation: split into n_splits folds."""
    n_splits = params.get("n_splits", 5)
    fold_size = len(prices) // n_splits
    fold_results = []

    for i in range(n_splits):
        train_end = (i + 1) * fold_size
        test_start = train_end
        test_end = min(test_start + fold_size, len(prices))

        test_prices = prices.iloc[test_start:test_end]
        if len(test_prices) < 30:
            continue

        bench_slice = None
        if benchmark is not None and not benchmark.empty:
            bench_slice = benchmark.iloc[test_start:test_end]

        trades, equity_curve, metrics = algo.run(test_prices, bench_slice)
        fold_results.append(
            {
                "fold": i + 1,
                "period": f"{test_prices.index[0].date()} ~ {test_prices.index[-1].date()}",
                "trades": [t.__dict__ for t in trades],
                "equity_curve": equity_curve,
                "metrics": metrics.__dict__,
            }
        )

    all_returns = [f["metrics"]["total_return_pct"] for f in fold_results]
    avg_metrics = {}
    if all_returns:
        avg_metrics = {
            "avg_return_pct": sum(all_returns) / len(all_returns),
            "worst_fold_return": min(all_returns),
            "best_fold_return": max(all_returns),
        }

    return {"fold_results": fold_results, "avg_metrics": avg_metrics}


def _run_optimize(AlgoClass, base_params, trade_params, prices, benchmark, params):
    """Grid search for optimal parameters."""
    grid = params.get("grid", {})
    if not grid:
        return {"best_params": base_params, "best_metrics": {}, "all_results": []}

    best_result = None
    best_sharpe = float("-inf")
    all_results = []

    keys = list(grid.keys())
    values = list(grid.values())

    for combo in itertools.product(*values):
        test_params = {**base_params, **dict(zip(keys, combo))}
        algo = AlgoClass(test_params, trade_params)
        try:
            trades, equity_curve, metrics = algo.run(prices, benchmark)
            result = {
                "params": test_params,
                "metrics": metrics.__dict__,
            }
            all_results.append(result)
            if metrics.sharpe_ratio > best_sharpe:
                best_sharpe = metrics.sharpe_ratio
                best_result = result
        except Exception:
            continue

    return {
        "best_params": best_result["params"] if best_result else base_params,
        "best_metrics": best_result["metrics"] if best_result else {},
        "all_results": all_results[:50],
    }
