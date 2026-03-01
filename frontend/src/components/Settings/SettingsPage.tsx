export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Settings</h2>
        <p className="text-sm text-slate-500">
          Configure your daily briefing preferences
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* News Topics */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            News Topics
          </h3>
          <p className="text-sm text-slate-400">
            Topic selection coming in Phase 7...
          </p>
        </div>

        {/* Stock Watchlist */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            Stock Watchlist
          </h3>
          <p className="text-sm text-slate-400">
            Watchlist management coming in Phase 7...
          </p>
        </div>

        {/* News Sources */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            News Sources
          </h3>
          <p className="text-sm text-slate-400">
            RSS source configuration coming in Phase 7...
          </p>
        </div>
      </div>
    </div>
  );
}
