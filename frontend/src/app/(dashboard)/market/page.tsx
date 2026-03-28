"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { CandlestickChart } from "@/components/charts/CandlestickChart";

export default function MarketPage() {
  const [search, setSearch] = useState("");
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [market, setMarket] = useState("");

  const { data: stocks } = useQuery({
    queryKey: ["stocks", search, market],
    queryFn: () =>
      api
        .get("/market/stocks", {
          params: { search: search || undefined, market: market || undefined, limit: 50 },
        })
        .then((r) => r.data),
  });

  const { data: priceData } = useQuery({
    queryKey: ["price", selectedTicker],
    queryFn: () =>
      api
        .get(`/market/stocks/${selectedTicker}/price`, {
          params: { timeframe: "1D" },
        })
        .then((r) => r.data),
    enabled: !!selectedTicker,
  });

  const chartData =
    priceData?.map((p: any) => ({
      time: p.date,
      open: p.open,
      high: p.high,
      low: p.low,
      close: p.close,
    })) || [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Market</h1>

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search ticker or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 max-w-sm px-4 py-2 bg-bg-card border border-border rounded-lg text-white focus:outline-none focus:border-blue-500"
        />
        <select
          value={market}
          onChange={(e) => setMarket(e.target.value)}
          className="px-4 py-2 bg-bg-card border border-border rounded-lg text-white"
        >
          <option value="">All Markets</option>
          <option value="KOSPI">KOSPI</option>
          <option value="KOSDAQ">KOSDAQ</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Stock List */}
        <div className="bg-bg-card border border-border rounded-xl p-4 max-h-[600px] overflow-auto">
          <h2 className="text-sm font-semibold text-gray-400 mb-3">
            Stocks ({stocks?.total || 0})
          </h2>
          <div className="space-y-1">
            {stocks?.items?.map((s: any) => (
              <button
                key={s.ticker}
                onClick={() => setSelectedTicker(s.ticker)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  selectedTicker === s.ticker
                    ? "bg-blue-600/20 text-blue-400"
                    : "hover:bg-bg-hover text-gray-300"
                }`}
              >
                <div className="flex justify-between">
                  <span className="font-medium">{s.ticker}</span>
                  <span className="text-xs text-gray-500">{s.market}</span>
                </div>
                <div className="text-xs text-gray-500 truncate">{s.name}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        <div className="lg:col-span-2 bg-bg-card border border-border rounded-xl p-4">
          {selectedTicker ? (
            <>
              <h2 className="text-lg font-semibold mb-3">{selectedTicker}</h2>
              {chartData.length > 0 ? (
                <CandlestickChart data={chartData} height={500} />
              ) : (
                <div className="h-[500px] flex items-center justify-center text-gray-500">
                  Loading chart data...
                </div>
              )}
            </>
          ) : (
            <div className="h-[500px] flex items-center justify-center text-gray-500">
              Select a stock to view chart
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
