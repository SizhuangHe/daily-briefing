import { Lightbulb, Loader2, Quote, RefreshCw, Sparkles } from "lucide-react";
import { useInspiration, useRefreshInspiration } from "../../hooks/useInspiration";

export default function InspirationSection() {
  const { data, isLoading } = useInspiration();
  const refreshMutation = useRefreshInspiration();

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">
          Daily Inspiration
        </h3>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
        >
          <RefreshCw
            className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`}
          />
          Shuffle
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-6">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      ) : !data ? (
        <p className="text-sm text-slate-400">No inspiration available.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          {/* Quote */}
          {data.quote && (
            <div className="rounded-lg border border-amber-100 bg-gradient-to-br from-amber-50 to-yellow-50 p-4">
              <div className="mb-2 flex items-center gap-1.5">
                <Quote className="h-4 w-4 text-amber-600" />
                <span className="text-xs font-semibold text-amber-800">
                  Quote of the Day
                </span>
              </div>
              <p className="text-sm leading-relaxed text-slate-700 italic">
                "{data.quote.text}"
              </p>
              {data.quote.author && (
                <p className="mt-2 text-xs text-slate-500">
                  — {data.quote.author}
                </p>
              )}
            </div>
          )}

          {/* Fun Fact */}
          {data.fun_fact && (
            <div className="rounded-lg border border-teal-100 bg-gradient-to-br from-teal-50 to-emerald-50 p-4">
              <div className="mb-2 flex items-center gap-1.5">
                <Lightbulb className="h-4 w-4 text-teal-600" />
                <span className="text-xs font-semibold text-teal-800">
                  Fun Fact
                </span>
              </div>
              <p className="text-sm leading-relaxed text-slate-700">
                {data.fun_fact}
              </p>
            </div>
          )}

          {/* Activity */}
          {data.activity && (
            <div className="rounded-lg border border-violet-100 bg-gradient-to-br from-violet-50 to-purple-50 p-4">
              <div className="mb-2 flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-violet-600" />
                <span className="text-xs font-semibold text-violet-800">
                  Try This Today
                </span>
              </div>
              <p className="text-sm leading-relaxed text-slate-700">
                {data.activity}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
