from datetime import datetime
from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = "SIM"  # SIM or REAL
    initial_balance: int = 10_000_000
    kis_account_no: str | None = None
    kis_app_key: str | None = None
    kis_app_secret: str | None = None


class AccountResponse(BaseModel):
    id: int
    name: str
    type: str
    initial_balance: int
    cash_balance: int
    is_active: bool

    model_config = {"from_attributes": True}


class PositionResponse(BaseModel):
    id: int
    ticker: str
    qty: int
    avg_price: float
    current_price: float | None = None
    unrealized_pnl: float | None = None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    ticker: str
    side: str
    qty: int
    price: float
    filled_qty: int
    filled_price: float | None = None
    status: str
    pnl: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
