import { Clock, ExternalLink, MapPin } from "lucide-react";
import type { BriefArticle } from "../../types/briefing";

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

function timeAgo(dateStr?: string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function BriefArticleCard({
  article,
  variant = "normal",
}: {
  article: BriefArticle;
  variant?: "urgent" | "affects_you" | "normal";
}) {
  const severityStyle =
    SEVERITY_STYLES[article.severity || "medium"] || SEVERITY_STYLES.medium;

  return (
    <div
      className={`rounded-md border border-slate-100 border-l-[3px] bg-white px-4 py-3 transition-colors hover:bg-slate-50/60 ${severityStyle}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {/* Title */}
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-1.5 text-sm font-medium text-slate-800 hover:text-blue-700"
          >
            <span className="line-clamp-2">{article.title}</span>
            <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-slate-300 opacity-0 transition-opacity group-hover:opacity-100" />
          </a>

          {/* Summary */}
          {article.gemini_summary && (
            <p className="mt-1 text-xs leading-relaxed text-slate-500 line-clamp-2">
              {article.gemini_summary}
            </p>
          )}

          {/* Why it matters - shown for urgent/affects_you, calm tone */}
          {article.why_it_matters &&
            (variant === "urgent" || variant === "affects_you") && (
              <p className="mt-1 text-xs text-slate-400 italic">
                {article.why_it_matters}
              </p>
            )}

          {/* Meta row */}
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            {article.source_name && <span>{article.source_name}</span>}
            {article.published_at && (
              <span className="flex items-center gap-0.5">
                <Clock className="h-3 w-3" />
                {timeAgo(article.published_at)}
              </span>
            )}
            {article.geo_scope && article.geo_scope !== "global" && (
              <span className="flex items-center gap-0.5">
                <MapPin className="h-3 w-3" />
                {article.geo_scope.toUpperCase()}
              </span>
            )}
            {article.confirmed_sources >= 2 && (
              <span className="text-slate-500">
                {article.confirmed_sources} sources
              </span>
            )}
          </div>
        </div>

        {/* Event type badge */}
        {article.event_type && (
          <span
            className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${
              EVENT_TYPE_COLORS[article.event_type] || "bg-slate-100 text-slate-600"
            }`}
          >
            {EVENT_TYPE_LABELS[article.event_type] || article.event_type}
          </span>
        )}
      </div>
    </div>
  );
}
