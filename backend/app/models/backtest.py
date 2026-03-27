import enum
from datetime import date, datetime
from sqlalchemy import (
    String, Integer, Float, Date, DateTime, Enum, JSON,
    ForeignKey, Index, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class BacktestStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ValidationMode(str, enum.Enum):
    SIMPLE = "SIMPLE"
    WALK_FORWARD = "WALK_FORWARD"
    OPTIMIZE = "OPTIMIZE"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[BacktestStatus] = mapped_column(
        Enum(BacktestStatus), default=BacktestStatus.PENDING, nullable=False
    )
    validation_mode: Mapped[ValidationMode] = mapped_column(
        Enum(ValidationMode), default=ValidationMode.SIMPLE, nullable=False
    )
    validation_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Run config
    tickers: Mapped[list] = mapped_column(JSON, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    benchmark_ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Results stored as JSON for flexible structure
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    strategy: Mapped["Strategy"] = relationship(back_populates="backtest_runs")  # noqa: F821
    metrics: Mapped["BacktestMetrics | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
    trades: Mapped[list["BacktestTrade"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    equity_curve: Mapped[list["BacktestEquityCurve"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_backtest_runs_user_status", "user_id", "status"),
        Index("ix_backtest_runs_created_at", "created_at"),
    )


class BacktestMetrics(Base):
    __tablename__ = "backtest_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_return_pct: Mapped[float] = mapped_column(Float, nullable=False)
    annualized_return: Mapped[float] = mapped_column(Float, nullable=False)
    benchmark_return: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    mdd_pct: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_holding_days: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    run: Mapped["BacktestRun"] = relationship(back_populates="metrics")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY / SELL
    price: Mapped[float] = mapped_column(Float, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)

    run: Mapped["BacktestRun"] = relationship(back_populates="trades")

    __table_args__ = (
        Index("ix_backtest_trades_run_id", "run_id"),
    )


class BacktestEquityCurve(Base):
    __tablename__ = "backtest_equity_curve"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False)
    portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)

    run: Mapped["BacktestRun"] = relationship(back_populates="equity_curve")

    __table_args__ = (
        Index("ix_backtest_equity_run_id", "run_id"),
    )
