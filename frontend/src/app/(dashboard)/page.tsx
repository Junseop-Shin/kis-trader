"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

function StatCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-5">
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color || "text-white"}`}>
        {value}
      </div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get("/accounts/").then((r) => r.data),
  });

  const { data: activations } = useQuery({
    queryKey: ["active-strategies"],
    queryFn: () => api.get("/trading/active").then((r) => r.data),
  });

  const totalValue = accounts?.reduce(
    (sum: number, a: any) => sum + a.cash_balance,
    0
  ) || 0;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Portfolio Value"
          value={`${totalValue.toLocaleString()} KRW`}
        />
        <StatCard
          label="Accounts"
          value={String(accounts?.length || 0)}
          sub="SIM + REAL"
        />
        <StatCard
          label="Active Strategies"
          value={String(activations?.length || 0)}
          color="text-green-400"
        />
        <StatCard label="Today's P&L" value="--" sub="Market closed" />
      </div>

      {/* Accounts Table */}
      <div className="bg-bg-card border border-border rounded-xl p-5 mb-6">
        <h2 className="text-lg font-semibold mb-4">Accounts</h2>
        {accounts?.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-border">
                <th className="text-left py-2">Name</th>
                <th className="text-left py-2">Type</th>
                <th className="text-right py-2">Cash Balance</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((a: any) => (
                <tr key={a.id} className="border-b border-border/50">
                  <td className="py-2">{a.name}</td>
                  <td className="py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        a.type === "REAL"
                          ? "bg-red-500/20 text-red-400"
                          : "bg-blue-500/20 text-blue-400"
                      }`}
                    >
                      {a.type}
                    </span>
                  </td>
                  <td className="py-2 text-right">
                    {a.cash_balance.toLocaleString()} KRW
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500">
            No accounts yet. Create one in Settings.
          </p>
        )}
      </div>

      {/* Active Strategies */}
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-4">Active Strategies</h2>
        {activations?.length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {activations.map((a: any) => (
              <div
                key={a.id}
                className="border border-border rounded-lg p-4 bg-bg-secondary"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Strategy #{a.strategy_id}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">
                    {a.status}
                  </span>
                </div>
                <div className="text-sm text-gray-400">
                  Tickers: {a.tickers?.join(", ")}
                </div>
                {a.last_signal_date && (
                  <div className="text-xs text-gray-500 mt-1">
                    Last signal: {a.last_signal_action} on {a.last_signal_date}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No active strategies.</p>
        )}
      </div>
    </div>
  );
}
