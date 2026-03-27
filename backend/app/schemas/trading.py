from pydantic import BaseModel, Field


class ActivateStrategyRequest(BaseModel):
    strategy_id: int
    account_id: int
    tickers: list[str] = Field(min_length=1)
    config: dict | None = None


class DeactivateStrategyRequest(BaseModel):
    activation_id: int


class ActivationResponse(BaseModel):
    id: int
    strategy_id: int
    account_id: int
    status: str
    tickers: list[str]
    last_signal_date: str | None = None
    last_signal_action: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class NotificationSettingsUpdate(BaseModel):
    trade_signal: bool = True
    order_filled: bool = True
    daily_report: bool = True
    anomaly_alert: bool = True
    weekly_report: bool = False
    crash_threshold: float = -0.05
    portfolio_crash_threshold: float = -0.10
    auto_sell_on_crash: bool = False
