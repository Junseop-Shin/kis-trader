from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class TradeRecord:
    date: str
    ticker: str
    action: str  # BUY | SELL
    price: float
    qty: int
    pnl: float
    balance_after: float


@dataclass
class BacktestMetrics:
    total_return_pct: float
    annualized_return: float
    benchmark_return: float
    alpha: float
    mdd_pct: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_holding_days: float


class BaseAlgorithm(ABC):
    def __init__(self, params: dict, trade_params: dict):
        self.params = params
        self.initial_capital = trade_params.get("initial_capital", 10_000_000)
        self.position_size_pct = trade_params.get("position_size_pct", 0.1)
        self.stop_loss_pct = trade_params.get("stop_loss_pct", 0.03)
        self.take_profit_pct = trade_params.get("take_profit_pct", 0.10)
        self.commission_pct = trade_params.get("commission_pct", 0.00015)
        self.tax_pct = trade_params.get("tax_pct", 0.002)
        self.slippage_pct = trade_params.get("slippage_pct", 0.001)

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return Series with values: 1=BUY, -1=SELL, 0=HOLD"""
        pass

    def run(
        self, df: pd.DataFrame, benchmark_df: pd.DataFrame | None = None
    ) -> tuple[list[TradeRecord], list[dict], BacktestMetrics]:
        signals = self.generate_signals(df)
        trades, equity_curve = self._simulate(df, signals)
        metrics = self._calc_metrics(equity_curve, trades, benchmark_df)
        return trades, equity_curve, metrics

    def _simulate(
        self, df: pd.DataFrame, signals: pd.Series
    ) -> tuple[list[TradeRecord], list[dict]]:
        capital = float(self.initial_capital)
        position = 0
        avg_price = 0.0
        equity_curve: list[dict] = []
        trades: list[TradeRecord] = []
        entry_date: str | None = None

        for i, (date_idx, row) in enumerate(df.iterrows()):
            price = float(row["close"])
            signal = int(signals.iloc[i]) if i < len(signals) else 0

            # Check stop-loss / take-profit on existing position
            if position > 0 and avg_price > 0:
                pnl_pct = (price - avg_price) / avg_price
                if pnl_pct <= -self.stop_loss_pct or pnl_pct >= self.take_profit_pct:
                    signal = -1

            if signal == 1 and position == 0:
                buy_price = price * (1 + self.slippage_pct)
                invest = capital * self.position_size_pct
                qty = int(invest / buy_price)
                if qty > 0:
                    cost = qty * buy_price * (1 + self.commission_pct)
                    if cost <= capital:
                        capital -= cost
                        position = qty
                        avg_price = buy_price
                        entry_date = str(date_idx)[:10]
                        trades.append(
                            TradeRecord(
                                date=str(date_idx)[:10],
                                ticker="",
                                action="BUY",
                                price=round(buy_price, 2),
                                qty=qty,
                                pnl=0,
                                balance_after=round(capital + position * price, 2),
                            )
                        )

            elif signal == -1 and position > 0:
                sell_price = price * (1 - self.slippage_pct)
                proceeds = position * sell_price * (1 - self.commission_pct - self.tax_pct)
                pnl = proceeds - (position * avg_price)
                capital += proceeds
                trades.append(
                    TradeRecord(
                        date=str(date_idx)[:10],
                        ticker="",
                        action="SELL",
                        price=round(sell_price, 2),
                        qty=position,
                        pnl=round(pnl, 2),
                        balance_after=round(capital, 2),
                    )
                )
                position = 0
                avg_price = 0.0
                entry_date = None

            total_value = capital + position * price
            equity_curve.append(
                {"date": str(date_idx)[:10], "portfolio_value": round(total_value, 2)}
            )

        return trades, equity_curve

    def _calc_metrics(
        self,
        equity_curve: list[dict],
        trades: list[TradeRecord],
        benchmark_df: pd.DataFrame | None = None,
    ) -> BacktestMetrics:
        if not equity_curve:
            return BacktestMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        values = pd.Series([e["portfolio_value"] for e in equity_curve])
        total_return = (values.iloc[-1] / self.initial_capital - 1) * 100
        n_days = len(values)
        annualized = (
            ((values.iloc[-1] / self.initial_capital) ** (252 / max(n_days, 1)) - 1) * 100
        )

        # MDD
        peak = values.expanding().max()
        drawdown = (values - peak) / peak
        mdd = float(drawdown.min()) * 100

        # Sharpe
        daily_returns = values.pct_change().dropna()
        sharpe = 0.0
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = float(daily_returns.mean() / daily_returns.std() * np.sqrt(252))

        # Win rate
        sell_trades = [t for t in trades if t.action == "SELL"]
        wins = [t for t in sell_trades if t.pnl > 0]
        win_rate = (len(wins) / len(sell_trades) * 100) if sell_trades else 0

        # Profit factor
        gross_profit = sum(t.pnl for t in sell_trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in sell_trades if t.pnl < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        if profit_factor == float("inf"):
            profit_factor = 999.99

        # Benchmark
        benchmark_return = 0.0
        if benchmark_df is not None and not benchmark_df.empty:
            benchmark_return = float(
                (benchmark_df["close"].iloc[-1] / benchmark_df["close"].iloc[0] - 1) * 100
            )

        alpha = total_return - benchmark_return

        # Avg holding days
        buy_trades = [t for t in trades if t.action == "BUY"]
        avg_holding = 0.0
        if sell_trades and buy_trades:
            holding_days = []
            for idx, sell in enumerate(sell_trades):
                if idx < len(buy_trades):
                    d = (pd.Timestamp(sell.date) - pd.Timestamp(buy_trades[idx].date)).days
                    holding_days.append(d)
            avg_holding = float(np.mean(holding_days)) if holding_days else 0

        return BacktestMetrics(
            total_return_pct=round(total_return, 4),
            annualized_return=round(annualized, 4),
            benchmark_return=round(benchmark_return, 4),
            alpha=round(alpha, 4),
            mdd_pct=round(mdd, 4),
            sharpe_ratio=round(sharpe, 4),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            total_trades=len(sell_trades),
            avg_holding_days=round(avg_holding, 2),
        )
