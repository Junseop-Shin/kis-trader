"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { StrategyForm } from "@/components/backtest/StrategyForm";

export default function StrategiesPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategyConfig, setStrategyConfig] = useState<any>(null);

  const { data: strategies } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.get("/strategies/").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post("/strategies/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      setShowCreate(false);
      setName("");
      setDescription("");
      setStrategyConfig(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/strategies/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategies"] }),
  });

  const handleCreate = () => {
    if (!name || !strategyConfig) return;
    createMutation.mutate({
      name,
      description,
      ...strategyConfig,
    });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Strategies</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
        >
          {showCreate ? "Cancel" : "New Strategy"}
        </button>
      </div>

      {showCreate && (
        <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Create Strategy</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
                placeholder="My RSI Strategy"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Description
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
                placeholder="Optional description"
              />
            </div>
          </div>
          <StrategyForm onSubmit={setStrategyConfig} />
          {strategyConfig && (
            <button
              onClick={handleCreate}
              disabled={!name || createMutation.isPending}
              className="mt-4 w-full py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium disabled:opacity-50"
            >
              {createMutation.isPending ? "Creating..." : "Save Strategy"}
            </button>
          )}
        </div>
      )}

      {/* Strategy List */}
      <div className="space-y-3">
        {strategies?.map((s: any) => (
          <div
            key={s.id}
            className="bg-bg-card border border-border rounded-xl p-5 flex items-center justify-between"
          >
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="font-semibold">{s.name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-400">
                  {s.algorithm_type}
                </span>
              </div>
              {s.description && (
                <p className="text-sm text-gray-500">{s.description}</p>
              )}
              <div className="text-xs text-gray-600 mt-1">
                Params: {JSON.stringify(s.params)}
              </div>
            </div>
            <div className="flex gap-2">
              <a
                href={`/strategies/${s.id}`}
                className="px-3 py-1 text-sm border border-border rounded hover:bg-bg-hover"
              >
                View
              </a>
              <button
                onClick={() => deleteMutation.mutate(s.id)}
                className="px-3 py-1 text-sm border border-red-500/30 rounded text-red-400 hover:bg-red-500/10"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
        {!strategies?.length && (
          <p className="text-gray-500 text-center py-8">
            No strategies yet. Create one above.
          </p>
        )}
      </div>
    </div>
  );
}
