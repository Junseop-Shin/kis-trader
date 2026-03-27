"use client";

interface Metrics {
  total_return_pct: number;
  annualized_return: number;
  benchmark_return: number;
  alpha: number;
  mdd_pct: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  avg_holding_days: number;
}

interface MetricsGridProps {
  metrics: Metrics;
}

function MetricCard({
  label,
  value,
  suffix,
  positive,
}: {
  label: string;
  value: string;
  suffix?: string;
  positive?: boolean | null;
}) {
  const color =
    positive === true
      ? "text-green-400"
      : positive === false
      ? "text-red-400"
      : "text-white";
  return (
    <div className="bg-bg-secondary border border-border rounded-lg p-3">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-lg font-bold ${color}`}>
        {value}
        {suffix && <span className="text-sm font-normal">{suffix}</span>}
      </div>
    </div>
  );
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      <MetricCard
        label="Total Return"
        value={metrics.total_return_pct.toFixed(2)}
        suffix="%"
        positive={metrics.total_return_pct > 0}
      />
      <MetricCard
        label="Annualized Return"
        value={metrics.annualized_return.toFixed(2)}
        suffix="%"
        positive={metrics.annualized_return > 0}
      />
      <MetricCard
        label="Alpha"
        value={metrics.alpha.toFixed(2)}
        suffix="%"
        positive={metrics.alpha > 0}
      />
      <MetricCard
        label="Max Drawdown"
        value={metrics.mdd_pct.toFixed(2)}
        suffix="%"
        positive={false}
      />
      <MetricCard
        label="Sharpe Ratio"
        value={metrics.sharpe_ratio.toFixed(2)}
        positive={metrics.sharpe_ratio > 1 ? true : metrics.sharpe_ratio < 0 ? false : null}
      />
      <MetricCard
        label="Win Rate"
        value={metrics.win_rate.toFixed(1)}
        suffix="%"
        positive={metrics.win_rate > 50}
      />
      <MetricCard
        label="Profit Factor"
        value={metrics.profit_factor.toFixed(2)}
        positive={metrics.profit_factor > 1}
      />
      <MetricCard
        label="Total Trades"
        value={String(metrics.total_trades)}
        positive={null}
      />
      <MetricCard
        label="Avg Holding"
        value={metrics.avg_holding_days.toFixed(1)}
        suffix=" days"
        positive={null}
      />
      <MetricCard
        label="Benchmark Return"
        value={metrics.benchmark_return.toFixed(2)}
        suffix="%"
        positive={null}
      />
    </div>
  );
}
