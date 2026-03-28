import enum
from datetime import date, datetime
from sqlalchemy import (
    String, Integer, BigInteger, Float, Date, DateTime,
    Enum, ForeignKey, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class AccountType(str, enum.Enum):
    REAL = "REAL"
    SIM = "SIM"


class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)

    # KIS account info (encrypted, only for REAL accounts)
    kis_account_no: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kis_app_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    kis_app_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    kis_access_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    kis_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Balance
    initial_balance: Mapped[int] = mapped_column(BigInteger, default=10_000_000, nullable=False)
    cash_balance: Mapped[int] = mapped_column(BigInteger, default=10_000_000, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="accounts")  # noqa: F821
    positions: Mapped[list["Position"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_accounts_user_type", "user_id", "type"),
    )


class Position(TimestampMixin, Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    current_price: Mapped[float] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="positions")

    __table_args__ = (
        Index("ix_positions_account_ticker", "account_id", "ticker", unique=True),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    strategy_activation_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_activations.id"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    filled_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filled_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    kis_order_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped["Account"] = relationship(back_populates="orders")

    __table_args__ = (
        Index("ix_orders_account_status", "account_id", "status"),
        Index("ix_orders_created_at", "created_at"),
    )


class AccountDaily(Base):
    __tablename__ = "account_daily"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cash_balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stock_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    daily_pnl: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    daily_return_pct: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    __table_args__ = (
        Index("ix_account_daily_account_date", "account_id", "date", unique=True),
    )
