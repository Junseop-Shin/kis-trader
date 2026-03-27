from datetime import date

import pandas as pd
import pandas_ta as ta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..schemas.market import (
    PriceDailyResponse,
    SectorResponse,
    StockListResponse,
    StockResponse,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/stocks", response_model=StockListResponse)
async def list_stocks(
    market: str | None = None,
    sector: str | None = None,
    per_min: float | None = None,
    per_max: float | None = None,
    pbr_min: float | None = None,
    pbr_max: float | None = None,
    roe_min: float | None = None,
    volume_min: int | None = None,
    market_cap_min: int | None = None,
    market_cap_max: int | None = None,
    search: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List stocks with optional filters including fundamentals."""
    conditions = ["s.is_active = true"]
    params: dict = {}

    if market:
        conditions.append("s.market = :market")
        params["market"] = market
    if sector:
        conditions.append("s.sector = :sector")
        params["sector"] = sector
    if search:
        conditions.append("(s.ticker LIKE :search OR s.name LIKE :search)")
        params["search"] = f"%{search}%"

    # Join with fundamentals for filter criteria
    fund_join = ""
    if any(v is not None for v in [per_min, per_max, pbr_min, pbr_max, roe_min, market_cap_min, market_cap_max]):
        fund_join = (
            "LEFT JOIN LATERAL ("
            "  SELECT * FROM stock_fundamentals f WHERE f.ticker = s.ticker "
            "  ORDER BY f.date DESC LIMIT 1"
            ") sf ON true"
        )
        if per_min is not None:
            conditions.append("sf.per >= :per_min")
            params["per_min"] = per_min
        if per_max is not None:
            conditions.append("sf.per <= :per_max")
            params["per_max"] = per_max
        if pbr_min is not None:
            conditions.append("sf.pbr >= :pbr_min")
            params["pbr_min"] = pbr_min
        if pbr_max is not None:
            conditions.append("sf.pbr <= :pbr_max")
            params["pbr_max"] = pbr_max
        if roe_min is not None:
            conditions.append("sf.roe >= :roe_min")
            params["roe_min"] = roe_min
        if market_cap_min is not None:
            conditions.append("sf.market_cap >= :market_cap_min")
            params["market_cap_min"] = market_cap_min
        if market_cap_max is not None:
            conditions.append("sf.market_cap <= :market_cap_max")
            params["market_cap_max"] = market_cap_max

    # Volume filter uses latest price data
    vol_join = ""
    if volume_min is not None:
        vol_join = (
            "LEFT JOIN LATERAL ("
            "  SELECT volume FROM price_daily pd WHERE pd.ticker = s.ticker "
            "  ORDER BY pd.date DESC LIMIT 1"
            ") pv ON true"
        )
        conditions.append("pv.volume >= :volume_min")
        params["volume_min"] = volume_min

    where_clause = " AND ".join(conditions)

    # Count query
    count_sql = f"SELECT COUNT(*) FROM stocks s {fund_join} {vol_join} WHERE {where_clause}"
    count_result = await db.execute(text(count_sql), params)
    total = count_result.scalar()

    # Data query
    data_sql = (
        f"SELECT s.id, s.ticker, s.name, s.market, s.sector "
        f"FROM stocks s {fund_join} {vol_join} "
        f"WHERE {where_clause} "
        f"ORDER BY s.ticker "
        f"LIMIT :limit OFFSET :offset"
    )
    params["limit"] = limit
    params["offset"] = offset
    result = await db.execute(text(data_sql), params)
    rows = result.fetchall()

    items = [
        StockResponse(id=r[0], ticker=r[1], name=r[2], market=r[3], sector=r[4])
        for r in rows
    ]
    return StockListResponse(items=items, total=total)


@router.get("/stocks/{ticker}/price", response_model=list[PriceDailyResponse])
async def get_stock_price(
    ticker: str,
    timeframe: str = Query("1D", regex="^(1D|1W|1M)$"),
    start: date | None = None,
    end: date | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get OHLCV price timeseries for a stock."""
    conditions = ["ticker = :ticker"]
    params: dict = {"ticker": ticker}

    if start:
        conditions.append("date >= :start")
        params["start"] = start
    if end:
        conditions.append("date <= :end")
        params["end"] = end

    where = " AND ".join(conditions)
    sql = f"SELECT date, open, high, low, close, volume, change_pct FROM price_daily WHERE {where} ORDER BY date"
    result = await db.execute(text(sql), params)
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")

    if timeframe == "1D":
        return [
            PriceDailyResponse(
                date=r[0], open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5], change_pct=r[6]
            )
            for r in rows
        ]

    # Resample for weekly or monthly
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "change_pct"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    freq = "W" if timeframe == "1W" else "ME"
    resampled = df.resample(freq).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
        "change_pct": "last",
    }).dropna(subset=["open"])

    return [
        PriceDailyResponse(
            date=idx.date(),
            open=int(row["open"]),
            high=int(row["high"]),
            low=int(row["low"]),
            close=int(row["close"]),
            volume=int(row["volume"]),
            change_pct=row["change_pct"],
        )
        for idx, row in resampled.iterrows()
    ]


@router.get("/stocks/{ticker}/indicators")
async def get_stock_indicators(
    ticker: str,
    indicators: str = Query("ma", description="Comma-separated: ma,rsi,macd,bbands"),
    ma_periods: str = Query("5,20,60"),
    start: date | None = None,
    end: date | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Calculate technical indicators for a stock."""
    conditions = ["ticker = :ticker"]
    params: dict = {"ticker": ticker}
    if start:
        conditions.append("date >= :start")
        params["start"] = start
    if end:
        conditions.append("date <= :end")
        params["end"] = end

    where = " AND ".join(conditions)
    sql = f"SELECT date, open, high, low, close, volume FROM price_daily WHERE {where} ORDER BY date"
    result = await db.execute(text(sql), params)
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])

    ind_list = [s.strip() for s in indicators.split(",")]
    response: dict = {"dates": [d.strftime("%Y-%m-%d") for d in df["date"]]}

    if "ma" in ind_list:
        periods = [int(p) for p in ma_periods.split(",")]
        for p in periods:
            sma = df["close"].rolling(p).mean()
            response[f"sma_{p}"] = [round(v, 2) if pd.notna(v) else None for v in sma]

    if "rsi" in ind_list:
        rsi = ta.rsi(df["close"], length=14)
        response["rsi_14"] = [round(v, 2) if pd.notna(v) else None for v in rsi]

    if "macd" in ind_list:
        macd_df = ta.macd(df["close"])
        if macd_df is not None:
            response["macd"] = [round(v, 2) if pd.notna(v) else None for v in macd_df.iloc[:, 0]]
            response["macd_signal"] = [round(v, 2) if pd.notna(v) else None for v in macd_df.iloc[:, 2]]
            response["macd_hist"] = [round(v, 2) if pd.notna(v) else None for v in macd_df.iloc[:, 1]]

    if "bbands" in ind_list:
        bb = ta.bbands(df["close"], length=20, std=2.0)
        if bb is not None:
            response["bb_upper"] = [round(v, 2) if pd.notna(v) else None for v in bb.iloc[:, 2]]
            response["bb_middle"] = [round(v, 2) if pd.notna(v) else None for v in bb.iloc[:, 1]]
            response["bb_lower"] = [round(v, 2) if pd.notna(v) else None for v in bb.iloc[:, 0]]

    return response


@router.get("/sectors", response_model=list[SectorResponse])
async def list_sectors(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List sectors with stock counts."""
    sql = (
        "SELECT s.sector, COUNT(*) as cnt "
        "FROM stocks s WHERE s.is_active = true AND s.sector IS NOT NULL "
        "GROUP BY s.sector ORDER BY cnt DESC"
    )
    result = await db.execute(text(sql))
    rows = result.fetchall()

    return [
        SectorResponse(sector=r[0], stock_count=r[1], avg_change_pct=None)
        for r in rows
    ]
