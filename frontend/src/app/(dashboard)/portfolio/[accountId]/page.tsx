"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export default function PortfolioPage() {
  const { accountId } = useParams();

  const { data: account } = useQuery({
    queryKey: ["account", accountId],
    queryFn: () => api.get(`/accounts/${accountId}`).then((r) => r.data),
  });

  const { data: positions } = useQuery({
    queryKey: ["positions", accountId],
    queryFn: () =>
      api.get(`/accounts/${accountId}/positions`).then((r) => r.data),
  });

  const { data: orders } = useQuery({
    queryKey: ["orders", accountId],
    queryFn: () =>
      api
        .get(`/accounts/${accountId}/orders`, { params: { limit: 30 } })
        .then((r) => r.data),
  });

  if (!account) {
    return <div className="text-gray-500">Loading...</div>;
  }

  const stockValue = positions?.reduce(
    (sum: number, p: any) => sum + (p.current_price || 0) * p.qty,
    0
  ) || 0;
  const totalValue = account.cash_balance + stockValue;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        Portfolio: {account.name}
        <span className="ml-2 text-sm px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
          {account.type}
        </span>
      </h1>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-gray-400">Total Value</div>
          <div className="text-xl font-bold">
            {totalValue.toLocaleString()} KRW
          </div>
        </div>
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-gray-400">Cash</div>
          <div className="text-xl font-bold">
            {account.cash_balance.toLocaleString()} KRW
          </div>
        </div>
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-gray-400">Stock Value</div>
          <div className="text-xl font-bold">
            {stockValue.toLocaleString()} KRW
          </div>
        </div>
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <div className="text-sm text-gray-400">Return</div>
          <div
            className={`text-xl font-bold ${
              totalValue >= account.initial_balance
                ? "text-green-400"
                : "text-red-400"
            }`}
          >
            {(
              ((totalValue - account.initial_balance) /
                account.initial_balance) *
              100
            ).toFixed(2)}
            %
          </div>
        </div>
      </div>

      {/* Positions */}
      <div className="bg-bg-card border border-border rounded-xl p-5 mb-6">
        <h2 className="text-lg font-semibold mb-3">Positions</h2>
        {positions?.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-border">
                <th className="text-left py-2">Ticker</th>
                <th className="text-right py-2">Qty</th>
                <th className="text-right py-2">Avg Price</th>
                <th className="text-right py-2">Current</th>
                <th className="text-right py-2">P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p: any) => (
                <tr key={p.id} className="border-b border-border/30">
                  <td className="py-2 font-medium">{p.ticker}</td>
                  <td className="text-right">{p.qty}</td>
                  <td className="text-right">
                    {p.avg_price.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td className="text-right">
                    {(p.current_price || 0).toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td
                    className={`text-right ${
                      (p.unrealized_pnl || 0) >= 0
                        ? "text-green-400"
                        : "text-red-400"
                    }`}
                  >
                    {(p.unrealized_pnl || 0).toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500">No open positions</p>
        )}
      </div>

      {/* Recent Orders */}
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-3">Recent Orders</h2>
        {orders?.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-border">
                <th className="text-left py-2">Date</th>
                <th className="text-left py-2">Ticker</th>
                <th className="text-left py-2">Side</th>
                <th className="text-right py-2">Qty</th>
                <th className="text-right py-2">Price</th>
                <th className="text-left py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o: any) => (
                <tr key={o.id} className="border-b border-border/30">
                  <td className="py-1.5 text-xs text-gray-400">
                    {o.created_at?.slice(0, 10)}
                  </td>
                  <td>{o.ticker}</td>
                  <td>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${
                        o.side === "BUY"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {o.side}
                    </span>
                  </td>
                  <td className="text-right">{o.qty}</td>
                  <td className="text-right">
                    {o.price.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td className="text-xs text-gray-400">{o.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500">No orders yet</p>
        )}
      </div>
    </div>
  );
}
