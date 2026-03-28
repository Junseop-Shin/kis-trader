from datetime import date, datetime
from sqlalchemy import (
    String, Integer, BigInteger, Float, Date, DateTime, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class Stock(TimestampMixin, Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # KOSPI / KOSDAQ
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        Index("ix_stocks_market_sector", "market", "sector"),
    )


class PriceDaily(Base):
    """
    TimescaleDB hypertable: partitioned by date with 1-month chunks.
    CREATE after table: SELECT create_hypertable('price_daily', 'date',
        chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
    """
    __tablename__ = "price_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    open: Mapped[int] = mapped_column(Integer, nullable=False)
    high: Mapped[int] = mapped_column(Integer, nullable=False)
    low: Mapped[int] = mapped_column(Integer, nullable=False)
    close: Mapped[int] = mapped_column(Integer, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_price_daily_ticker_date"),
        Index("ix_price_daily_ticker_date_desc", "ticker", date.desc()),
    )


class PriceMinute(Base):
    """
    TimescaleDB hypertable: partitioned by datetime with 1-day chunks.
    CREATE after table: SELECT create_hypertable('price_minute', 'datetime',
        chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
    """
    __tablename__ = "price_minute"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    open: Mapped[int] = mapped_column(Integer, nullable=False)
    high: Mapped[int] = mapped_column(Integer, nullable=False)
    low: Mapped[int] = mapped_column(Integer, nullable=False)
    close: Mapped[int] = mapped_column(Integer, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "datetime", name="uq_price_minute_ticker_datetime"),
        Index("ix_price_minute_ticker_datetime_desc", "ticker", datetime.desc()),
    )


class StockFundamentals(TimestampMixin, Base):
    __tablename__ = "stock_fundamentals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    per: Mapped[float | None] = mapped_column(Float, nullable=True)
    pbr: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps: Mapped[float | None] = mapped_column(Float, nullable=True)
    bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    div_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_fundamentals_ticker_date"),
    )
