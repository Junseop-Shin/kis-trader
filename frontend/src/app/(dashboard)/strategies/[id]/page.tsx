"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export default function StrategyDetailPage() {
  const { id } = useParams();

  const { data: strategy } = useQuery({
    queryKey: ["strategy", id],
    queryFn: () => api.get(`/strategies/${id}`).then((r) => r.data),
  });

  if (!strategy) {
    return <div className="text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{strategy.name}</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-3">Algorithm</h2>
          <div className="text-sm space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400">Type</span>
              <span className="text-purple-400">{strategy.algorithm_type}</span>
            </div>
            {Object.entries(strategy.params).map(([key, val]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-400">{key}</span>
                <span>{String(val)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-bg-card border border-border rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-3">Trade Parameters</h2>
          <div className="text-sm space-y-2">
            {Object.entries(strategy.trade_params).map(([key, val]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-400">{key}</span>
                <span>
                  {typeof val === "number" && val < 1
                    ? `${(val as number * 100).toFixed(1)}%`
                    : typeof val === "number"
                    ? (val as number).toLocaleString()
                    : String(val)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex gap-3">
        <a
          href={`/backtest/new?strategy_id=${id}`}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
        >
          Run Backtest
        </a>
        <a
          href={`/trading?strategy_id=${id}`}
          className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm"
        >
          Activate for Trading
        </a>
      </div>
    </div>
  );
}
