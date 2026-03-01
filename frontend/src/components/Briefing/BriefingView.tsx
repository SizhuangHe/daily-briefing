import { Loader2, Newspaper } from "lucide-react";
import { useBriefing } from "../../hooks/useBriefing";
import BriefingSectionCard from "./BriefingSectionCard";

export default function BriefingView() {
  const { data: briefing, isLoading, isError } = useBriefing();

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

  const hasUrgent = briefing.urgent.articles.length > 0;
  const hasAffects = briefing.affects_you.articles.length > 0;
  const hasInterests = briefing.interests.articles.length > 0;

  if (!hasUrgent && !hasAffects && !hasInterests) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2">
          <Newspaper className="h-5 w-5 text-slate-400" />
          <h3 className="text-lg font-semibold text-slate-900">
            Daily Briefing
          </h3>
        </div>
        <p className="mt-2 text-sm text-slate-400">
          No briefing data yet. Refresh news to generate your briefing.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Overview */}
      {briefing.overview && (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <Newspaper className="h-4 w-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900">
              Today's Overview
            </h3>
          </div>
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
