import enum
from datetime import datetime
from sqlalchemy import (
    String, Enum, JSON, ForeignKey, Index, DateTime, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ActivationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class StrategyActivation(Base):
    __tablename__ = "strategy_activations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ActivationStatus] = mapped_column(
        Enum(ActivationStatus), default=ActivationStatus.ACTIVE, nullable=False
    )
    tickers: Mapped[list] = mapped_column(JSON, nullable=False)
    last_signal_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_signal_action: Mapped[str | None] = mapped_column(String(10), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    strategy: Mapped["Strategy"] = relationship()  # noqa: F821
    account: Mapped["Account"] = relationship()  # noqa: F821

    __table_args__ = (
        Index("ix_activations_account_status", "account_id", "status"),
    )
