"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/api";

export default function BacktestNewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const presetStrategyId = searchParams.get("strategy_id");

  const [strategyId, setStrategyId] = useState(presetStrategyId || "");
  const [tickers, setTickers] = useState("005930");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2025-12-31");
  const [benchmark, setBenchmark] = useState("069500");
  const [validationType, setValidationType] = useState("SIMPLE");
  const [nSplits, setNSplits] = useState(5);
  const [error, setError] = useState("");

  const { data: strategies } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.get("/strategies/").then((r) => r.data),
  });

  const runMutation = useMutation({
    mutationFn: (data: any) => api.post("/backtest/run", data),
    onSuccess: (res) => {
      router.push(`/backtest/${res.data.id}`);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || "Failed to start backtest");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const tickerList = tickers
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    if (!strategyId || tickerList.length === 0) {
      setError("Strategy and at least one ticker are required");
      return;
    }

    const payload: any = {
      strategy_id: parseInt(strategyId),
      tickers: tickerList,
      start_date: startDate,
      end_date: endDate,
      benchmark_ticker: benchmark || null,
      validation_type: validationType,
    };

    if (validationType === "WALK_FORWARD") {
      payload.validation_params = { n_splits: nSplits };
    }

    runMutation.mutate(payload);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">New Backtest</h1>

      <form
        onSubmit={handleSubmit}
        className="bg-bg-card border border-border rounded-xl p-6 max-w-2xl space-y-4"
      >
        {/* Strategy */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Strategy</label>
          <select
            value={strategyId}
            onChange={(e) => setStrategyId(e.target.value)}
            className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white"
            required
          >
            <option value="">Select a strategy...</option>
            {strategies?.map((s: any) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.algorithm_type})
              </option>
            ))}
          </select>
        </div>

        {/* Tickers */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Tickers (comma-separated)
          </label>
          <input
            type="text"
            value={tickers}
            onChange={(e) => setTickers(e.target.value)}
            className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white"
            placeholder="005930, 035420"
          />
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white"
            />
          </div>
        </div>

        {/* Benchmark */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Benchmark Ticker (optional)
          </label>
          <input
            type="text"
            value={benchmark}
            onChange={(e) => setBenchmark(e.target.value)}
            className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white"
            placeholder="069500 (KODEX 200)"
          />
        </div>

        {/* Validation Type */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            Validation Type
          </label>
          <div className="flex gap-2">
            {["SIMPLE", "WALK_FORWARD", "OPTIMIZE"].map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setValidationType(type)}
                className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                  validationType === type
                    ? "border-blue-500 bg-blue-500/20 text-blue-400"
                    : "border-border bg-bg-secondary text-gray-400"
                }`}
              >
                {type.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {validationType === "WALK_FORWARD" && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">
              Number of Folds
            </label>
            <input
              type="number"
              value={nSplits}
              onChange={(e) => setNSplits(parseInt(e.target.value) || 5)}
              min={2}
              max={20}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white"
            />
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={runMutation.isPending}
          className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
        >
          {runMutation.isPending ? "Starting..." : "Run Backtest"}
        </button>
      </form>
    </div>
  );
}
