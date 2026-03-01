import { Loader2, RefreshCw } from "lucide-react";
import { useIndices, useWatchlist } from "../../hooks/useStocks";
import IndexCard from "./IndexCard";
import WatchlistTable from "./WatchlistTable";

export default function StocksSection() {
  const { data: indices, isLoading: indicesLoading, refetch: refetchIndices } = useIndices();
  const { data: watchlist, isLoading: watchlistLoading, refetch: refetchWatchlist } = useWatchlist();

  const isLoading = indicesLoading || watchlistLoading;

  const handleRefresh = () => {
    refetchIndices();
    refetchWatchlist();
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">
          Market Overview
        </h3>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          title="Refresh"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Major Indices */}
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {indicesLoading ? (
          <div className="col-span-full flex justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : (
          indices?.map((idx) => <IndexCard key={idx.symbol} index={idx} />)
        )}
      </div>

      {/* Watchlist */}
      <div>
        <h4 className="mb-3 text-sm font-semibold text-slate-700">
          Watchlist
        </h4>
        {watchlistLoading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : (
          <WatchlistTable items={watchlist ?? []} />
        )}
      </div>
    </div>
  );
}
