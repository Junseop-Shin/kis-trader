from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    algorithm_type: str
    params: dict = {}
    trade_params: dict = {}
    custom_code: str | None = None


class StrategyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    params: dict | None = None
    trade_params: dict | None = None
    custom_code: str | None = None


class StrategyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None = None
    algorithm_type: str
    params: dict
    trade_params: dict
    custom_code: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}
