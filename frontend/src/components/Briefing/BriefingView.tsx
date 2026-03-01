import { Loader2, Newspaper, RefreshCw } from "lucide-react";
import { useBriefing } from "../../hooks/useBriefing";
import { useRefreshNews } from "../../hooks/useNews";
import BriefingSectionCard from "./BriefingSectionCard";

export default function BriefingView() {
  const { data: briefing, isLoading, isError } = useBriefing();
  const refreshMutation = useRefreshNews();

  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          Building your daily briefing...
        </div>
      </div>
    );
  }

  if (isError || !briefing) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-400">
          Unable to load briefing. Try refreshing the page.
        </p>
      </div>
    );
  }

  const hasUrgent = briefing.urgent.stories.length > 0;
  const hasAffects = briefing.affects_you.stories.length > 0;
  const hasInterests = briefing.interests.stories.length > 0;

  if (!hasUrgent && !hasAffects && !hasInterests) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-slate-400" />
            <h3 className="text-lg font-semibold text-slate-900">
              Daily Briefing
            </h3>
          </div>
          <button
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
          >
            {refreshMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {refreshMutation.isPending ? "Fetching..." : "Refresh"}
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-400">
          No briefing data yet. Click Refresh to fetch news and generate your briefing.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="h-5 w-5 text-slate-600" />
          <h3 className="text-lg font-semibold text-slate-900">
            Daily Briefing
          </h3>
        </div>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
        >
          {refreshMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          {refreshMutation.isPending ? "Fetching..." : "Refresh"}
        </button>
      </div>

      {/* Overview */}
      {briefing.overview && (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm leading-relaxed text-slate-700">
            {briefing.overview}
          </p>
        </div>
      )}

      {/* Urgent */}
      {hasUrgent && <BriefingSectionCard section={briefing.urgent} />}

      {/* Affects You */}
      {hasAffects && <BriefingSectionCard section={briefing.affects_you} />}

      {/* Your Interests */}
      {hasInterests && <BriefingSectionCard section={briefing.interests} />}
    </div>
  );
}
