"use client";

import { useState } from "react";

const ALGORITHM_DEFAULTS: Record<
  string,
  { label: string; params: { key: string; label: string; type: string; default: any; min?: number; max?: number; step?: number; options?: string[]; recommended?: any }[] }
> = {
  MA_CROSS: {
    label: "MA Crossover",
    params: [
      { key: "short_period", label: "Short MA Period", type: "number", default: 5, min: 2, max: 50, recommended: 5 },
      { key: "long_period", label: "Long MA Period", type: "number", default: 20, min: 5, max: 200, recommended: 20 },
      { key: "ma_type", label: "MA Type", type: "select", options: ["SMA", "EMA"], default: "SMA" },
    ],
  },
  RSI: {
    label: "RSI",
    params: [
      { key: "period", label: "Period", type: "number", default: 14, min: 2, max: 50, recommended: 14 },
      { key: "oversold", label: "Oversold Level", type: "number", default: 30, min: 10, max: 50, recommended: 30 },
      { key: "overbought", label: "Overbought Level", type: "number", default: 70, min: 50, max: 90, recommended: 70 },
    ],
  },
  MACD: {
    label: "MACD",
    params: [
      { key: "fast", label: "Fast EMA", type: "number", default: 12, recommended: 12 },
      { key: "slow", label: "Slow EMA", type: "number", default: 26, recommended: 26 },
      { key: "signal", label: "Signal", type: "number", default: 9, recommended: 9 },
    ],
  },
  BOLLINGER: {
    label: "Bollinger Bands",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, recommended: 20 },
      { key: "std_dev", label: "Std Dev Multiplier", type: "number", default: 2.0, step: 0.1, recommended: 2.0 },
      { key: "mode", label: "Strategy Mode", type: "select", options: ["reversion", "breakout"], default: "reversion" },
    ],
  },
  MOMENTUM: {
    label: "Momentum (ROC)",
    params: [
      { key: "period", label: "ROC Period", type: "number", default: 12, recommended: 12 },
      { key: "buy_threshold", label: "Buy Threshold (%)", type: "number", default: 0, step: 0.5 },
      { key: "sell_threshold", label: "Sell Threshold (%)", type: "number", default: 0, step: 0.5 },
    ],
  },
  STOCHASTIC: {
    label: "Stochastic Oscillator",
    params: [
      { key: "k_period", label: "%K Period", type: "number", default: 14, recommended: 14 },
      { key: "d_period", label: "%D Period", type: "number", default: 3, recommended: 3 },
      { key: "oversold", label: "Oversold", type: "number", default: 20, recommended: 20 },
      { key: "overbought", label: "Overbought", type: "number", default: 80, recommended: 80 },
    ],
  },
  MEAN_REVERT: {
    label: "Mean Reversion (Z-Score)",
    params: [
      { key: "lookback", label: "Lookback Period", type: "number", default: 20, recommended: 20 },
      { key: "entry_z", label: "Entry Z-Score", type: "number", default: -2.0, step: 0.1 },
      { key: "exit_z", label: "Exit Z-Score", type: "number", default: 0.0, step: 0.1 },
    ],
  },
};

interface StrategyFormProps {
  onSubmit: (data: {
    algorithm_type: string;
    params: Record<string, any>;
    trade_params: Record<string, any>;
  }) => void;
}

export function StrategyForm({ onSubmit }: StrategyFormProps) {
  const [algorithmType, setAlgorithmType] = useState("MA_CROSS");
  const [params, setParams] = useState<Record<string, any>>({});
  const [tradeParams, setTradeParams] = useState({
    initial_capital: 10_000_000,
    position_size_pct: 0.1,
    stop_loss_pct: 0.03,
    take_profit_pct: 0.1,
  });

  const algoDef = ALGORITHM_DEFAULTS[algorithmType];

  const handleAlgoChange = (type: string) => {
    setAlgorithmType(type);
    const defaults: Record<string, any> = {};
    ALGORITHM_DEFAULTS[type]?.params.forEach((p) => {
      defaults[p.key] = p.default;
    });
    setParams(defaults);
  };

  const handleSubmit = () => {
    onSubmit({
      algorithm_type: algorithmType,
      params: { ...getDefaults(), ...params },
      trade_params: tradeParams,
    });
  };

  const getDefaults = () => {
    const defaults: Record<string, any> = {};
    algoDef?.params.forEach((p) => {
      defaults[p.key] = p.default;
    });
    return defaults;
  };

  return (
    <div className="space-y-6">
      {/* Algorithm Selector */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">Algorithm</label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {Object.entries(ALGORITHM_DEFAULTS).map(([key, def]) => (
            <button
              key={key}
              onClick={() => handleAlgoChange(key)}
              className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
                algorithmType === key
                  ? "border-blue-500 bg-blue-500/20 text-blue-400"
                  : "border-border bg-bg-secondary text-gray-400 hover:border-gray-500"
              }`}
            >
              {def.label}
            </button>
          ))}
        </div>
      </div>

      {/* Algorithm Parameters */}
      {algoDef && (
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            Parameters
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {algoDef.params.map((p) => (
              <div key={p.key}>
                <label className="block text-xs text-gray-500 mb-1">
                  {p.label}
                  {p.recommended !== undefined && (
                    <span className="text-blue-400 ml-1">
                      (rec: {p.recommended})
                    </span>
                  )}
                </label>
                {p.type === "select" ? (
                  <select
                    value={params[p.key] ?? p.default}
                    onChange={(e) =>
                      setParams({ ...params, [p.key]: e.target.value })
                    }
                    className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
                  >
                    {p.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={params[p.key] ?? p.default}
                    onChange={(e) =>
                      setParams({
                        ...params,
                        [p.key]: parseFloat(e.target.value) || 0,
                      })
                    }
                    min={p.min}
                    max={p.max}
                    step={p.step || 1}
                    className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trade Parameters */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">
          Trade Parameters
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Initial Capital (KRW)
            </label>
            <input
              type="number"
              value={tradeParams.initial_capital}
              onChange={(e) =>
                setTradeParams({
                  ...tradeParams,
                  initial_capital: parseInt(e.target.value) || 0,
                })
              }
              className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Position Size (%)
            </label>
            <input
              type="number"
              value={tradeParams.position_size_pct * 100}
              onChange={(e) =>
                setTradeParams({
                  ...tradeParams,
                  position_size_pct: (parseFloat(e.target.value) || 0) / 100,
                })
              }
              min={1}
              max={100}
              className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Stop Loss (%)
            </label>
            <input
              type="number"
              value={tradeParams.stop_loss_pct * 100}
              onChange={(e) =>
                setTradeParams({
                  ...tradeParams,
                  stop_loss_pct: (parseFloat(e.target.value) || 0) / 100,
                })
              }
              min={0}
              max={50}
              step={0.5}
              className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Take Profit (%)
            </label>
            <input
              type="number"
              value={tradeParams.take_profit_pct * 100}
              onChange={(e) =>
                setTradeParams({
                  ...tradeParams,
                  take_profit_pct: (parseFloat(e.target.value) || 0) / 100,
                })
              }
              min={0}
              max={100}
              step={0.5}
              className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
            />
          </div>
        </div>
      </div>

      <button
        onClick={handleSubmit}
        className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium"
      >
        Apply Strategy Settings
      </button>
    </div>
  );
}
