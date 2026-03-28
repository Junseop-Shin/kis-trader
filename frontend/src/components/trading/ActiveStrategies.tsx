"use client";

interface Activation {
  id: number;
  strategy_id: number;
  account_id: number;
  status: string;
  tickers: string[];
  last_signal_date: string | null;
  last_signal_action: string | null;
}

interface ActiveStrategiesProps {
  activations: Activation[];
  onDeactivate: (id: number) => void;
}

export function ActiveStrategies({
  activations,
  onDeactivate,
}: ActiveStrategiesProps) {
  if (!activations.length) {
    return <p className="text-gray-500 text-sm">No active strategies</p>;
  }

  return (
    <div className="space-y-3">
      {activations.map((a) => (
        <div
          key={a.id}
          className="flex items-center justify-between bg-bg-secondary border border-border rounded-lg p-4"
        >
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium">Strategy #{a.strategy_id}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded ${
                  a.status === "ACTIVE"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-yellow-500/20 text-yellow-400"
                }`}
              >
                {a.status}
              </span>
            </div>
            <div className="text-sm text-gray-400">
              Account #{a.account_id} | {a.tickers.join(", ")}
            </div>
            {a.last_signal_date && (
              <div className="text-xs text-gray-500 mt-1">
                Last: {a.last_signal_action} on {a.last_signal_date}
              </div>
            )}
          </div>
          <button
            onClick={() => onDeactivate(a.id)}
            className="px-3 py-1 text-sm border border-red-500/30 rounded text-red-400 hover:bg-red-500/10"
          >
            Stop
          </button>
        </div>
      ))}
    </div>
  );
}
