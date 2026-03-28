from datetime import date, datetime
from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    strategy_id: int
    tickers: list[str] = Field(min_length=1)
    start_date: date
    end_date: date
    benchmark_ticker: str | None = "069500"  # KODEX 200 ETF
    validation_type: str = "SIMPLE"  # SIMPLE, WALK_FORWARD, OPTIMIZE
    validation_params: dict | None = None


class BacktestCompareRequest(BaseModel):
    strategy_ids: list[int] = Field(min_length=2)
    tickers: list[str] = Field(min_length=1)
    start_date: date
    end_date: date
    benchmark_ticker: str | None = "069500"


class CounterfactualRequest(BaseModel):
    account_id: int
    strategy_ids: list[int] = Field(min_length=1)


class BacktestRunResponse(BaseModel):
    id: int
    strategy_id: int
    status: str
    tickers: list[str]
    start_date: date
    end_date: date
    validation_mode: str
    result_json: dict | None = None
    error_message: str | None = None
    celery_task_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class BacktestMetricsResponse(BaseModel):
    total_return_pct: float
    annualized_return: float
    benchmark_return: float
    alpha: float
    mdd_pct: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_holding_days: float

    model_config = {"from_attributes": True}
