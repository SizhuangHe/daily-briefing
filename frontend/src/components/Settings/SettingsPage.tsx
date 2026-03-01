import { useState } from "react";
import { Loader2, Plus, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";
import { useWatchlist } from "../../hooks/useStocks";
import {
  useAddSource,
  useDeleteSource,
  useSources,
  useToggleSource,
} from "../../hooks/usePreferences";
import WatchlistTable from "../Stocks/WatchlistTable";

function SourceManager() {
  const { data: sources, isLoading } = useSources();
  const addMutation = useAddSource();
  const toggleMutation = useToggleSource();
  const deleteMutation = useDeleteSource();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;
    addMutation.mutate(
      { name: name.trim(), url: url.trim(), source_type: "rss" },
      {
        onSuccess: () => {
          setName("");
          setUrl("");
        },
      }
    );
  };

  return (
    <div>
      {/* Add source form */}
      <form onSubmit={handleAdd} className="mb-4 flex gap-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Source name"
          className="w-40 rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="RSS feed URL"
          className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={addMutation.isPending || !name.trim() || !url.trim()}
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

      {/* Sources list */}
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        </div>
      ) : !sources?.length ? (
        <p className="text-sm text-slate-400">No sources configured.</p>
      ) : (
        <div className="overflow-hidden rounded-md border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-slate-500">
                  Name
                </th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">
                  URL
                </th>
                <th className="px-3 py-2 text-center font-medium text-slate-500">
                  Enabled
                </th>
                <th className="px-3 py-2 text-right font-medium text-slate-500"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sources.map((source) => (
                <tr key={source.id} className="hover:bg-slate-50">
                  <td className="px-3 py-2 font-medium text-slate-900">
                    {source.name}
                  </td>
                  <td className="max-w-xs truncate px-3 py-2 text-slate-500">
                    {source.url}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => toggleMutation.mutate(source.id)}
                      className="text-slate-500 hover:text-blue-600"
                      title={source.enabled ? "Disable" : "Enable"}
                    >
                      {source.enabled ? (
                        <ToggleRight className="h-5 w-5 text-blue-600" />
                      ) : (
                        <ToggleLeft className="h-5 w-5 text-slate-300" />
                      )}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => deleteMutation.mutate(source.id)}
                      className="text-slate-400 hover:text-red-500"
                      title="Delete source"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const { data: watchlist } = useWatchlist();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Settings</h2>
        <p className="text-sm text-slate-500">
          Configure your daily briefing preferences
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Stock Watchlist */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            Stock Watchlist
          </h3>
          <WatchlistTable items={watchlist || []} />
        </div>

        {/* News Sources */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            News Sources
          </h3>
          <p className="mb-4 text-sm text-slate-500">
            Manage RSS feeds. Toggle sources on/off or add new ones.
          </p>
          <SourceManager />
        </div>
      </div>
    </div>
  );
}
