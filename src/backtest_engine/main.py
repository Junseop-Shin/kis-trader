"""
Backtesting Engine — FastAPI server (Mac Mini)
Accepts a strategy definition + date range, runs simulation, returns metrics.
"""
import math
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np

app = FastAPI(title="KIS Backtesting Engine")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str                         # "YYYY-MM-DD"
    end_date: str                           # "YYYY-MM-DD"
    initial_capital: float = 10_000_000.0  # KRW
    strategy: dict[str, Any]               # e.g. {"type": "rsi", "period": 14, "oversold": 30, "overbought": 70}
    prices: list[dict[str, Any]]           # [{date, open, high, low, close, volume}, ...]


class TradeRecord(BaseModel):
    date: str
    action: str     # "BUY" | "SELL"
    price: float
    quantity: int
    capital_after: float


class BacktestResult(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_trades: int
    trades: list[TradeRecord]


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------

def _calc_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _run_rsi_strategy(df: pd.DataFrame, params: dict, initial_capital: float) -> tuple[list[TradeRecord], pd.Series]:
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)

    df = df.copy()
    df["rsi"] = _calc_rsi(df["close"], period)

    capital = initial_capital
    holdings = 0
    trades: list[TradeRecord] = []
    equity_curve = []

    for _, row in df.iterrows():
        price = row["close"]
        rsi = row["rsi"]

        if pd.isna(rsi):
            equity_curve.append(capital + holdings * price)
            continue

        if rsi < oversold and holdings == 0 and capital >= price:
            quantity = int(capital // price)
            capital -= quantity * price
            holdings += quantity
            trades.append(TradeRecord(
                date=str(row["date"]),
                action="BUY",
                price=price,
                quantity=quantity,
                capital_after=capital,
            ))

        elif rsi > overbought and holdings > 0:
            capital += holdings * price
            trades.append(TradeRecord(
                date=str(row["date"]),
                action="SELL",
                price=price,
                quantity=holdings,
                capital_after=capital,
            ))
            holdings = 0

        equity_curve.append(capital + holdings * price)

    # Liquidate remaining holdings at last price
    if holdings > 0:
        final_price = df["close"].iloc[-1]
        capital += holdings * final_price

    return trades, pd.Series(equity_curve, index=df.index)


def _run_strategy(df: pd.DataFrame, strategy: dict, initial_capital: float):
    stype = strategy.get("type", "rsi").lower()
    if stype == "rsi":
        return _run_rsi_strategy(df, strategy, initial_capital)
    raise HTTPException(status_code=400, detail=f"Unsupported strategy type: {stype}")


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def _max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max
    return float(drawdown.min() * 100)  # percent


def _sharpe(equity: pd.Series, risk_free_rate: float = 0.03) -> float:
    returns = equity.pct_change().dropna()
    if returns.std() == 0:
        return 0.0
    annualized = (returns.mean() - risk_free_rate / 252) / returns.std() * math.sqrt(252)
    return round(float(annualized), 4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "backtest-engine"}


@app.post("/backtest", response_model=BacktestResult)
def run_backtest(req: BacktestRequest):
    if not req.prices:
        raise HTTPException(status_code=400, detail="prices list is empty")

    df = pd.DataFrame(req.prices)
    required_cols = {"date", "close"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"prices must include columns: {required_cols}")

    df["close"] = df["close"].astype(float)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    trades, equity = _run_strategy(df, req.strategy, req.initial_capital)

    final_capital = float(equity.iloc[-1]) if len(equity) > 0 else req.initial_capital
    total_return = (final_capital - req.initial_capital) / req.initial_capital * 100

    return BacktestResult(
        ticker=req.ticker,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        final_capital=round(final_capital, 2),
        total_return_pct=round(total_return, 4),
        max_drawdown_pct=round(_max_drawdown(equity), 4),
        sharpe_ratio=_sharpe(equity),
        total_trades=len(trades),
        trades=trades,
    )
