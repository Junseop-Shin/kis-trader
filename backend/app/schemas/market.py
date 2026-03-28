from datetime import date
from pydantic import BaseModel


class StockResponse(BaseModel):
    id: int
    ticker: str
    name: str
    market: str
    sector: str | None = None

    model_config = {"from_attributes": True}


class StockListResponse(BaseModel):
    items: list[StockResponse]
    total: int


class PriceDailyResponse(BaseModel):
    date: date
    open: int
    high: int
    low: int
    close: int
    volume: int
    change_pct: float | None = None

    model_config = {"from_attributes": True}


class IndicatorRequest(BaseModel):
    indicators: list[str] = ["ma"]  # ma, rsi, macd, bbands
    ma_periods: list[int] = [5, 20, 60]


class SectorResponse(BaseModel):
    sector: str
    stock_count: int
    avg_change_pct: float | None = None
