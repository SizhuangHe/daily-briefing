import { useState } from "react";
import { Trash2, Plus, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import type { WatchlistItem } from "../../types/briefing";
import { useAddToWatchlist, useRemoveFromWatchlist } from "../../hooks/useStocks";

interface WatchlistTableProps {
  items: WatchlistItem[];
}

export default function WatchlistTable({ items }: WatchlistTableProps) {
  const [newSymbol, setNewSymbol] = useState("");
  const addMutation = useAddToWatchlist();
  const removeMutation = useRemoveFromWatchlist();

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const symbol = newSymbol.trim().toUpperCase();
    if (!symbol) return;
    addMutation.mutate(symbol);
    setNewSymbol("");
  };

  return (
    <div>
      {/* Add stock form */}
      <form onSubmit={handleAdd} className="mb-3 flex gap-2">
        <input
          type="text"
          value={newSymbol}
          onChange={(e) => setNewSymbol(e.target.value)}
          placeholder="Add symbol (e.g. AAPL)"
          className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={addMutation.isPending || !newSymbol.trim()}
          className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {addMutation.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
          Add
        </button>
      </form>

      {/* Watchlist table */}
      {items.length === 0 ? (
        <p className="text-sm text-slate-400">
          No stocks in watchlist. Add one above.
        </p>
      ) : (
        <div className="overflow-hidden rounded-md border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-500">
                  Symbol
                </th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">
                  Name
                </th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">
                  Price
                </th>
                <th className="px-3 py-2 text-right font-medium text-slate-500">
                  Change
                </th>
                <th className="px-3 py-2 text-right font-medium text-slate-500"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => {
                const isPositive = (item.change ?? 0) >= 0;
                return (
                  <tr key={item.symbol} className="hover:bg-slate-50">
                    <td className="px-3 py-2 font-semibold text-slate-900">
                      {item.symbol}
                    </td>
                    <td className="px-3 py-2 text-slate-600">
                      {item.name ?? "-"}
                    </td>
                    <td className="px-3 py-2 text-right font-medium text-slate-900">
                      {item.price?.toFixed(2) ?? "-"}
                    </td>
                    <td
                      className={clsx(
                        "px-3 py-2 text-right font-medium",
                        isPositive ? "text-emerald-600" : "text-red-600"
                      )}
                    >
                      {item.change != null
                        ? `${isPositive ? "+" : ""}${item.change.toFixed(2)} (${isPositive ? "+" : ""}${item.change_percent?.toFixed(2)}%)`
                        : "-"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => removeMutation.mutate(item.symbol)}
                        className="text-slate-400 hover:text-red-500"
                        title="Remove from watchlist"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
