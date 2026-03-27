"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";

export default function BacktestComparePage() {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [tickers, setTickers] = useState("005930");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");

  const { data: strategies } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.get("/strategies/").then((r) => r.data),
  });

  const compareMutation = useMutation({
    mutationFn: (data: any) => api.post("/backtest/compare", data),
  });

  const toggleStrategy = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleCompare = () => {
    if (selectedIds.length < 2) return;
    compareMutation.mutate({
      strategy_ids: selectedIds,
      tickers: tickers.split(",").map((t) => t.trim()),
      start_date: startDate,
      end_date: endDate,
    });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Compare Strategies</h1>

      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <h2 className="text-sm text-gray-400 mb-3">
          Select strategies to compare (min 2)
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-4">
          {strategies?.map((s: any) => (
            <button
              key={s.id}
              onClick={() => toggleStrategy(s.id)}
              className={`px-3 py-2 rounded-lg text-sm border text-left ${
                selectedIds.includes(s.id)
                  ? "border-blue-500 bg-blue-500/20 text-blue-400"
                  : "border-border bg-bg-secondary text-gray-400"
              }`}
            >
              <div className="font-medium">{s.name}</div>
              <div className="text-xs opacity-60">{s.algorithm_type}</div>
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tickers</label>
            <input
              type="text"
              value={tickers}
              onChange={(e) => setTickers(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Start</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">End</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            />
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={selectedIds.length < 2 || compareMutation.isPending}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
        >
          {compareMutation.isPending
            ? "Starting..."
            : `Compare ${selectedIds.length} Strategies`}
        </button>
      </div>

      {compareMutation.data && (
        <div className="bg-bg-card border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-3">Comparison Started</h2>
          <p className="text-sm text-gray-400 mb-3">
            {compareMutation.data.data.message}
          </p>
          <div className="space-y-2">
            {compareMutation.data.data.runs?.map((run: any) => (
              <a
                key={run.id}
                href={`/backtest/${run.id}`}
                className="block px-4 py-2 bg-bg-secondary border border-border rounded-lg hover:bg-bg-hover text-sm"
              >
                Run #{run.id} - Strategy #{run.strategy_id} ({run.status})
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
