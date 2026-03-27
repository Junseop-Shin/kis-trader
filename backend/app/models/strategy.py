import enum
from sqlalchemy import String, Enum, JSON, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class AlgorithmType(str, enum.Enum):
    MA_CROSS = "MA_CROSS"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER = "BOLLINGER"
    MOMENTUM = "MOMENTUM"
    STOCHASTIC = "STOCHASTIC"
    MEAN_REVERT = "MEAN_REVERT"
    MULTI = "MULTI"
    CUSTOM = "CUSTOM"


class Strategy(TimestampMixin, Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm_type: Mapped[AlgorithmType] = mapped_column(Enum(AlgorithmType), nullable=False)

    # Algorithm-specific parameters (e.g., {"short_period": 5, "long_period": 20})
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Trade parameters (e.g., {"initial_capital": 10000000, "position_size_pct": 0.1})
    trade_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Custom code (only for CUSTOM algorithm type)
    custom_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="strategies")  # noqa: F821
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(back_populates="strategy")  # noqa: F821

    __table_args__ = (
        Index("ix_strategies_user_algo", "user_id", "algorithm_type"),
    )
