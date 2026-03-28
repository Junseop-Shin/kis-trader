"use client";

interface Position {
  id: number;
  ticker: string;
  qty: number;
  avg_price: number;
  current_price: number | null;
  unrealized_pnl: number | null;
}

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  if (!positions.length) {
    return <p className="text-gray-500 text-sm">No open positions</p>;
  }

  const totalPnl = positions.reduce(
    (sum, p) => sum + (p.unrealized_pnl || 0),
    0
  );

  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-border">
            <th className="text-left py-2">Ticker</th>
            <th className="text-right py-2">Qty</th>
            <th className="text-right py-2">Avg Price</th>
            <th className="text-right py-2">Current</th>
            <th className="text-right py-2">P&L</th>
            <th className="text-right py-2">P&L %</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => {
            const pnlPct =
              p.avg_price > 0 && p.current_price
                ? ((p.current_price - p.avg_price) / p.avg_price) * 100
                : 0;
            return (
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
                <td
                  className={`text-right ${
                    pnlPct >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {pnlPct.toFixed(2)}%
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t border-border">
            <td colSpan={4} className="py-2 font-medium text-gray-400">
              Total
            </td>
            <td
              className={`text-right font-bold ${
                totalPnl >= 0 ? "text-green-400" : "text-red-400"
              }`}
            >
              {totalPnl.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
