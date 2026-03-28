"""
KOSPI/KOSDAQ data collector using pykrx.
Collects: stock list, 3-year daily OHLCV (adjusted), fundamentals (PER/PBR/ROE).
"""
import asyncio
import logging
from datetime import date, timedelta

import pandas as pd
from pykrx import stock as krx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)


def _get_engine(database_url: str):
    return create_async_engine(database_url, echo=False, pool_size=5)


def _get_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def collect_stock_list(session_factory) -> int:
    """Collect all KOSPI + KOSDAQ tickers and save to stocks table."""
    collected = 0
    for market in ["KOSPI", "KOSDAQ"]:
        tickers = krx.get_market_ticker_list(market=market)
        await asyncio.sleep(0.2)

        async with session_factory() as db:
            for ticker in tickers:
                name = krx.get_market_ticker_name(ticker)
                await asyncio.sleep(0.05)

                await db.execute(
                    text(
                        "INSERT INTO stocks (ticker, name, market, is_active, created_at, updated_at) "
                        "VALUES (:ticker, :name, :market, true, now(), now()) "
                        "ON CONFLICT (ticker) DO UPDATE SET name = :name, market = :market, "
                        "is_active = true, updated_at = now()"
                    ),
                    {"ticker": ticker, "name": name, "market": market},
                )
                collected += 1

            await db.commit()
            logger.info(f"Collected {len(tickers)} stocks from {market}")

    return collected


async def get_all_tickers(session_factory) -> list[str]:
    """Get all active tickers from the database."""
    async with session_factory() as db:
        result = await db.execute(
            text("SELECT ticker FROM stocks WHERE is_active = true ORDER BY ticker")
        )
        return [row[0] for row in result.fetchall()]


async def collect_daily_prices_bulk(
    session_factory, start: str, end: str, tickers: list[str] | None = None
) -> int:
    """
    Bulk collect daily OHLCV for all tickers between start and end dates.
    Uses adjusted prices. Rate limiting to avoid pykrx blocking.
    start/end format: "YYYYMMDD"
    """
    if tickers is None:
        tickers = await get_all_tickers(session_factory)

    total_inserted = 0
    batch_size = 50

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]

        async with session_factory() as db:
            for ticker in batch:
                try:
                    df = krx.get_market_ohlcv(start, end, ticker, adjusted=True)
                    await asyncio.sleep(0.15)

                    if df.empty:
                        continue

                    for idx, row in df.iterrows():
                        dt = idx.date() if hasattr(idx, "date") else idx
                        prev_close = None
                        change_pct = None

                        await db.execute(
                            text(
                                "INSERT INTO price_daily (ticker, date, open, high, low, close, volume, change_pct) "
                                "VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :change_pct) "
                                "ON CONFLICT ON CONSTRAINT uq_price_daily_ticker_date "
                                "DO UPDATE SET open = :open, high = :high, low = :low, "
                                "close = :close, volume = :volume, change_pct = :change_pct"
                            ),
                            {
                                "ticker": ticker,
                                "date": dt,
                                "open": int(row.get("시가", 0)),
                                "high": int(row.get("고가", 0)),
                                "low": int(row.get("저가", 0)),
                                "close": int(row.get("종가", 0)),
                                "volume": int(row.get("거래량", 0)),
                                "change_pct": float(row.get("등락률", 0)) if "등락률" in row.index else None,
                            },
                        )
                        total_inserted += 1

                except Exception as e:
                    logger.warning(f"Failed to collect prices for {ticker}: {e}")
                    continue

            await db.commit()
            logger.info(f"Batch {i // batch_size + 1}: collected prices for {len(batch)} tickers")

    logger.info(f"Total price records upserted: {total_inserted}")
    return total_inserted


async def collect_fundamentals(session_factory, target_date: str | None = None) -> int:
    """
    Collect PER, PBR, EPS, BPS, DIV for all tickers on given date.
    target_date format: "YYYYMMDD". Defaults to today.
    """
    if target_date is None:
        target_date = date.today().strftime("%Y%m%d")

    collected = 0

    for market in ["KOSPI", "KOSDAQ"]:
        try:
            df = krx.get_market_fundamental(target_date, market=market)
            await asyncio.sleep(0.3)

            if df.empty:
                continue

            # Market cap data
            cap_df = krx.get_market_cap(target_date, market=market)
            await asyncio.sleep(0.3)

            async with session_factory() as db:
                for ticker in df.index:
                    row = df.loc[ticker]
                    market_cap = int(cap_df.loc[ticker, "시가총액"]) if ticker in cap_df.index else None

                    await db.execute(
                        text(
                            "INSERT INTO stock_fundamentals "
                            "(ticker, date, per, pbr, eps, bps, div_yield, market_cap, created_at, updated_at) "
                            "VALUES (:ticker, :date, :per, :pbr, :eps, :bps, :div_yield, :market_cap, now(), now()) "
                            "ON CONFLICT ON CONSTRAINT uq_fundamentals_ticker_date "
                            "DO UPDATE SET per = :per, pbr = :pbr, eps = :eps, bps = :bps, "
                            "div_yield = :div_yield, market_cap = :market_cap, updated_at = now()"
                        ),
                        {
                            "ticker": ticker,
                            "date": pd.Timestamp(target_date).date(),
                            "per": float(row.get("PER", 0)) if row.get("PER", 0) != 0 else None,
                            "pbr": float(row.get("PBR", 0)) if row.get("PBR", 0) != 0 else None,
                            "eps": float(row.get("EPS", 0)) if row.get("EPS", 0) != 0 else None,
                            "bps": float(row.get("BPS", 0)) if row.get("BPS", 0) != 0 else None,
                            "div_yield": float(row.get("DIV", 0)) if row.get("DIV", 0) != 0 else None,
                            "market_cap": market_cap,
                        },
                    )
                    collected += 1

                await db.commit()
                logger.info(f"Collected fundamentals for {market}: {len(df)} tickers")

        except Exception as e:
            logger.error(f"Failed to collect fundamentals for {market}: {e}")

    return collected


async def collect_daily_update(session_factory) -> None:
    """Daily incremental update - called by scheduler at 16:00."""
    today = date.today().strftime("%Y%m%d")
    logger.info(f"Running daily update for {today}")
    await collect_daily_prices_bulk(session_factory, today, today)
    await collect_fundamentals(session_factory, today)
    logger.info("Daily update complete")


async def initial_bulk_load(session_factory) -> None:
    """
    Initial data load: 3 years of historical data.
    Should only be run once when the database is empty.
    """
    end = date.today()
    start = end - timedelta(days=365 * 3)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    logger.info(f"Starting initial bulk load: {start_str} to {end_str}")
    await collect_stock_list(session_factory)
    await collect_daily_prices_bulk(session_factory, start_str, end_str)
    await collect_fundamentals(session_factory)
    logger.info("Initial bulk load complete")


async def is_database_empty(session_factory) -> bool:
    """Check if the price_daily table has any data."""
    async with session_factory() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM price_daily LIMIT 1"))
        count = result.scalar()
        return count == 0
