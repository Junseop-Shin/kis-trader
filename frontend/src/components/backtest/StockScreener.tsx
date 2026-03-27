"use client";

import { useState } from "react";

interface StockScreenerProps {
  onSelect: (tickers: string[]) => void;
}

export function StockScreener({ onSelect }: StockScreenerProps) {
  const [filters, setFilters] = useState({
    market: "",
    sector: "",
    perMin: "",
    perMax: "",
    pbrMin: "",
    pbrMax: "",
    roeMin: "",
    volumeMin: "",
  });

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-gray-400">Stock Screener</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Market</label>
          <select
            value={filters.market}
            onChange={(e) =>
              setFilters({ ...filters, market: e.target.value })
            }
            className="w-full px-2 py-1.5 bg-bg-secondary border border-border rounded text-xs text-white"
          >
            <option value="">All</option>
            <option value="KOSPI">KOSPI</option>
            <option value="KOSDAQ">KOSDAQ</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">PER Min</label>
          <input
            type="number"
            value={filters.perMin}
            onChange={(e) =>
              setFilters({ ...filters, perMin: e.target.value })
            }
            className="w-full px-2 py-1.5 bg-bg-secondary border border-border rounded text-xs text-white"
            placeholder="0"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">PER Max</label>
          <input
            type="number"
            value={filters.perMax}
            onChange={(e) =>
              setFilters({ ...filters, perMax: e.target.value })
            }
            className="w-full px-2 py-1.5 bg-bg-secondary border border-border rounded text-xs text-white"
            placeholder="30"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">ROE Min (%)</label>
          <input
            type="number"
            value={filters.roeMin}
            onChange={(e) =>
              setFilters({ ...filters, roeMin: e.target.value })
            }
            className="w-full px-2 py-1.5 bg-bg-secondary border border-border rounded text-xs text-white"
            placeholder="10"
          />
        </div>
      </div>
      <p className="text-xs text-gray-600">
        Use the Market page to browse and filter stocks, then copy ticker codes here.
      </p>
    </div>
  );
}
