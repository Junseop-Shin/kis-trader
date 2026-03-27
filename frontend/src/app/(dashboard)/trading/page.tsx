"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

export default function TradingPage() {
  const queryClient = useQueryClient();
  const [strategyId, setStrategyId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [tickers, setTickers] = useState("");

  const { data: activations } = useQuery({
    queryKey: ["active-strategies"],
    queryFn: () => api.get("/trading/active").then((r) => r.data),
  });

  const { data: strategies } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.get("/strategies/").then((r) => r.data),
  });

  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => api.get("/accounts/").then((r) => r.data),
  });

  const activateMutation = useMutation({
    mutationFn: (data: any) => api.post("/trading/activate", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-strategies"] });
      setStrategyId("");
      setAccountId("");
      setTickers("");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) =>
      api.post("/trading/deactivate", { activation_id: id }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["active-strategies"] }),
  });

  const handleActivate = () => {
    if (!strategyId || !accountId || !tickers) return;
    activateMutation.mutate({
      strategy_id: parseInt(strategyId),
      account_id: parseInt(accountId),
      tickers: tickers.split(",").map((t) => t.trim()),
    });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Simulation Trading</h1>

      {/* Activate Form */}
      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Activate Strategy</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Strategy
            </label>
            <select
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            >
              <option value="">Select...</option>
              {strategies?.map((s: any) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Account</label>
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            >
              <option value="">Select...</option>
              {accounts?.map((a: any) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.type})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Tickers</label>
            <input
              type="text"
              value={tickers}
              onChange={(e) => setTickers(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
              placeholder="005930, 035420"
            />
          </div>
        </div>
        <button
          onClick={handleActivate}
          disabled={activateMutation.isPending}
          className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm disabled:opacity-50"
        >
          {activateMutation.isPending ? "Activating..." : "Activate"}
        </button>
      </div>

      {/* Active Strategies */}
      <div className="bg-bg-card border border-border rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Active Strategies</h2>
        {activations?.length ? (
          <div className="space-y-3">
            {activations.map((a: any) => (
              <div
                key={a.id}
                className="flex items-center justify-between bg-bg-secondary border border-border rounded-lg p-4"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium">
                      Strategy #{a.strategy_id}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">
                      {a.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400">
                    Account #{a.account_id} | Tickers: {a.tickers?.join(", ")}
                  </div>
                  {a.last_signal_date && (
                    <div className="text-xs text-gray-500 mt-1">
                      Last: {a.last_signal_action} on {a.last_signal_date}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => deactivateMutation.mutate(a.id)}
                  className="px-3 py-1 text-sm border border-red-500/30 rounded text-red-400 hover:bg-red-500/10"
                >
                  Stop
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No active strategies</p>
        )}
      </div>
    </div>
  );
}
