"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { MetricsGrid } from "@/components/charts/MetricsGrid";
import { EquityChart } from "@/components/charts/EquityChart";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { CandlestickChart } from "@/components/charts/CandlestickChart";

export default function BacktestResultPage() {
  const { id } = useParams();

  const { data: run, isLoading } = useQuery({
    queryKey: ["backtest-run", id],
    queryFn: () => api.get(`/backtest/runs/${id}`).then((r) => r.data),
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === "RUNNING" || data?.status === "PENDING" ? 3000 : false;
    },
  });

  if (isLoading) {
    return <div className="text-gray-500">Loading backtest results...</div>;
  }

  if (!run) {
    return <div className="text-red-400">Backtest run not found</div>;
  }

  if (run.status === "PENDING" || run.status === "RUNNING") {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="animate-spin w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full mb-4" />
        <p className="text-gray-400">Backtest is {run.status.toLowerCase()}...</p>
        <p className="text-xs text-gray-600 mt-2">
          Auto-refreshing every 3 seconds
        </p>
      </div>
    );
  }

  if (run.status === "FAILED") {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-red-400 mb-2">
          Backtest Failed
        </h2>
        <p className="text-sm text-gray-400">
          {run.error_message || "Unknown error"}
        </p>
      </div>
    );
  }

  const result = run.result_json;
  if (!result) {
    return <div className="text-gray-500">No results available</div>;
  }

  const metrics = result.metrics;
  const trades = result.trades || [];
  const equityCurve = result.equity_curve || [];

  // Prepare equity chart data
  const equityData = equityCurve.map((e: any) => ({
    time: e.date,
    value: e.portfolio_value,
  }));

  // Calculate drawdown from equity curve
  const drawdownData: { time: string; value: number }[] = [];
  let peak = 0;
  for (const point of equityCurve) {
    if (point.portfolio_value > peak) peak = point.portfolio_value;
    const dd = peak > 0 ? ((point.portfolio_value - peak) / peak) * 100 : 0;
    drawdownData.push({ time: point.date, value: dd });
  }

  // Buy/sell markers for candlestick chart
  const buyMarkers = trades
    .filter((t: any) => t.action === "BUY")
    .map((t: any) => ({
      time: t.date,
      position: "belowBar" as const,
      color: "#22c55e",
      shape: "arrowUp" as const,
      text: `B ${t.qty}`,
    }));

  const sellMarkers = trades
    .filter((t: any) => t.action === "SELL")
    .map((t: any) => ({
      time: t.date,
      position: "aboveBar" as const,
      color: "#ef4444",
      shape: "arrowDown" as const,
      text: `S ${t.qty}`,
    }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Backtest #{id}</h1>
        <span className="px-3 py-1 rounded bg-green-500/20 text-green-400 text-sm">
          {run.status}
        </span>
      </div>

      <div className="text-sm text-gray-400 mb-6">
        Tickers: {run.tickers?.join(", ")} | Period: {run.start_date} ~{" "}
        {run.end_date} | Mode: {run.validation_mode}
      </div>

      {/* Metrics Grid */}
      {metrics && (
        <div className="mb-6">
          <MetricsGrid metrics={metrics} />
        </div>
      )}

      {/* Equity Curve */}
      <div className="bg-bg-card border border-border rounded-xl p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Equity Curve</h2>
        <EquityChart data={equityData} height={300} />
      </div>

      {/* Drawdown */}
      <div className="bg-bg-card border border-border rounded-xl p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Drawdown</h2>
        <DrawdownChart data={drawdownData} height={200} />
      </div>

      {/* Trades Table */}
      <div className="bg-bg-card border border-border rounded-xl p-4">
        <h2 className="text-lg font-semibold mb-3">
          Trades ({trades.length})
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-border">
                <th className="text-left py-2">Date</th>
                <th className="text-left py-2">Action</th>
                <th className="text-right py-2">Price</th>
                <th className="text-right py-2">Qty</th>
                <th className="text-right py-2">P&L</th>
                <th className="text-right py-2">Balance</th>
              </tr>
            </thead>
            <tbody>
              {trades.slice(0, 100).map((t: any, i: number) => (
                <tr key={i} className="border-b border-border/30">
                  <td className="py-1.5">{t.date}</td>
                  <td>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        t.action === "BUY"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {t.action}
                    </span>
                  </td>
                  <td className="text-right">
                    {t.price.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td className="text-right">{t.qty}</td>
                  <td
                    className={`text-right ${
                      t.pnl > 0
                        ? "text-green-400"
                        : t.pnl < 0
                        ? "text-red-400"
                        : ""
                    }`}
                  >
                    {t.pnl
                      ? t.pnl.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })
                      : "-"}
                  </td>
                  <td className="text-right">
                    {t.balance_after.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {trades.length > 100 && (
            <p className="text-xs text-gray-500 mt-2 text-center">
              Showing 100 of {trades.length} trades
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
