import { useEffect, useRef, useState } from "react";
import { ExternalLink, Newspaper, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { BriefingStory, StorySource } from "../../types/briefing";
import { useRatings, useRateArticle } from "../../hooks/useNews";

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-l-slate-500",
  high: "border-l-slate-400",
  medium: "border-l-slate-300",
  low: "border-l-slate-200",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  disaster: "Disaster",
  public_safety: "Public Safety",
  health: "Health",
  weather: "Weather",
  infrastructure: "Infrastructure",
  war_conflict: "Conflict",
  policy: "Policy",
  financial_shock: "Financial",
  market: "Markets",
  tech: "Technology",
  science: "Science",
  crime: "Crime",
  diplomacy: "Diplomacy",
  sports: "Sports",
  entertainment: "Entertainment",
  general: "General",
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  disaster: "bg-slate-200 text-slate-700",
  public_safety: "bg-slate-200 text-slate-700",
  health: "bg-rose-50 text-rose-600",
  weather: "bg-sky-50 text-sky-600",
  infrastructure: "bg-amber-50 text-amber-600",
  war_conflict: "bg-slate-200 text-slate-700",
  policy: "bg-violet-50 text-violet-600",
  financial_shock: "bg-emerald-50 text-emerald-600",
  market: "bg-green-50 text-green-600",
  tech: "bg-blue-50 text-blue-600",
  science: "bg-teal-50 text-teal-600",
  crime: "bg-slate-200 text-slate-700",
};

function SourceItem({
  source,
  rating,
  onRate,
}: {
  source: StorySource;
  rating: number | null;
  onRate: (sourceId: number, score: number) => void;
}) {
  const timeAgo = source.published_at
    ? formatDistanceToNow(new Date(source.published_at), { addSuffix: true })
    : null;

  return (
    <div className="group rounded-md border border-slate-100 px-3 py-2.5 transition-colors hover:bg-slate-50">
      <div className="flex items-start gap-1.5">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="min-w-0 flex-1"
        >
          <h5 className="text-sm font-medium text-slate-800 group-hover:text-blue-600">
            {source.title}
          </h5>
        </a>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-slate-300 opacity-0 transition-opacity group-hover:opacity-100" />
        </a>
      </div>
      <div className="mt-1 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          {source.source_name && (
            <span className="font-medium text-slate-500">
              {source.source_name}
            </span>
          )}
          {timeAgo && <span>{timeAgo}</span>}
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => onRate(source.id, 1)}
            className={`rounded p-0.5 transition-colors ${
              rating === 1
                ? "bg-emerald-50 text-emerald-600"
                : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
            }`}
            title="Interested"
          >
            <ThumbsUp className="h-3 w-3" />
          </button>
          <button
            onClick={() => onRate(source.id, -1)}
            className={`rounded p-0.5 transition-colors ${
              rating === -1
                ? "bg-red-50 text-red-500"
                : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
            }`}
            title="Not interested"
          >
            <ThumbsDown className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

function SourcesPopover({
  sources,
  ratingsMap,
  onRate,
  onClose,
}: {
  sources: StorySource[];
  ratingsMap: Record<number, number> | undefined;
  onRate: (sourceId: number, score: number) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute left-0 top-full z-50 mt-1 w-[28rem] rounded-lg border border-slate-200 bg-white p-4 shadow-lg"
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500">
          {sources.length} source{sources.length !== 1 ? "s" : ""}
        </span>
        <button
          onClick={onClose}
          className="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="max-h-80 space-y-2 overflow-y-auto">
        {sources.map((source) => (
          <SourceItem
            key={source.id}
            source={source}
            rating={ratingsMap?.[source.id] ?? null}
            onRate={onRate}
          />
        ))}
      </div>
    </div>
  );
}

export default function StoryCard({
  story,
  variant = "normal",
}: {
  story: BriefingStory;
  variant?: "urgent" | "affects_you" | "normal";
}) {
  const [showSources, setShowSources] = useState(false);
  const { data: ratingsMap } = useRatings();
  const rateArticleMutation = useRateArticle();
  const severityStyle =
    SEVERITY_STYLES[story.severity || "medium"] || SEVERITY_STYLES.medium;

  const handleRateArticle = (articleId: number, score: number) => {
    const currentRating = ratingsMap?.[articleId] ?? null;
    const newScore = currentRating === score ? 0 : score;
    rateArticleMutation.mutate({ articleId, score: newScore });
  };

  return (
    <div
      className={`rounded-md border border-slate-100 border-l-[3px] bg-white px-4 py-3 ${severityStyle}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {/* Headline */}
          <h4 className="text-sm font-semibold text-slate-800">
            {story.headline}
          </h4>

          {/* Narrative */}
          <p className="mt-1 text-sm leading-relaxed text-slate-600">
            {story.narrative}
          </p>

          {/* Why it matters */}
          {story.why_it_matters &&
            (variant === "urgent" || variant === "affects_you") && (
              <p className="mt-1 text-xs text-slate-400 italic">
                {story.why_it_matters}
              </p>
            )}

          {/* Bottom row: sources */}
          <div className="relative mt-2">
            <div className="relative">
              {story.sources.length > 0 && (
                <>
                  <button
                    onClick={() => setShowSources(!showSources)}
                    className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  >
                    <Newspaper className="h-3 w-3" />
                    {story.sources.length} source
                    {story.sources.length !== 1 ? "s" : ""}
                  </button>

                  {showSources && (
                    <SourcesPopover
                      sources={story.sources}
                      ratingsMap={ratingsMap}
                      onRate={handleRateArticle}
                      onClose={() => setShowSources(false)}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Event type badge */}
        {story.event_type && (
          <span
            className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${
              EVENT_TYPE_COLORS[story.event_type] || "bg-slate-100 text-slate-600"
            }`}
          >
            {EVENT_TYPE_LABELS[story.event_type] || story.event_type}
          </span>
        )}
      </div>
    </div>
  );
}
