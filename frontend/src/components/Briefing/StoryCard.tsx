import { ExternalLink } from "lucide-react";
import type { BriefingStory } from "../../types/briefing";

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

export default function StoryCard({
  story,
  variant = "normal",
}: {
  story: BriefingStory;
  variant?: "urgent" | "affects_you" | "normal";
}) {
  const severityStyle =
    SEVERITY_STYLES[story.severity || "medium"] || SEVERITY_STYLES.medium;

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

          {/* Source links */}
          {story.sources.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
              <span className="text-slate-300">Sources:</span>
              {story.sources.map((source) => (
                <a
                  key={source.id}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group inline-flex items-center gap-0.5 text-slate-400 hover:text-blue-600"
                >
                  {source.source_name || "Link"}
                  <ExternalLink className="h-2.5 w-2.5 opacity-0 transition-opacity group-hover:opacity-100" />
                </a>
              ))}
            </div>
          )}
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
