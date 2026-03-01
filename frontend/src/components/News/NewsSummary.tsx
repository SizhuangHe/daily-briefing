import { Loader2, Sparkles } from "lucide-react";
import { useNewsSummary } from "../../hooks/useNews";

const TOPIC_COLORS: Record<string, string> = {
  technology: "bg-blue-100 text-blue-800 border-blue-200",
  tech: "bg-blue-100 text-blue-800 border-blue-200",
  ai: "bg-purple-100 text-purple-800 border-purple-200",
  finance: "bg-emerald-100 text-emerald-800 border-emerald-200",
  economy: "bg-emerald-100 text-emerald-800 border-emerald-200",
  markets: "bg-emerald-100 text-emerald-800 border-emerald-200",
  world: "bg-orange-100 text-orange-800 border-orange-200",
  politics: "bg-orange-100 text-orange-800 border-orange-200",
  geopolitics: "bg-orange-100 text-orange-800 border-orange-200",
  middle: "bg-orange-100 text-orange-800 border-orange-200",
  domestic: "bg-amber-100 text-amber-800 border-amber-200",
  social: "bg-amber-100 text-amber-800 border-amber-200",
  science: "bg-teal-100 text-teal-800 border-teal-200",
  health: "bg-rose-100 text-rose-800 border-rose-200",
  energy: "bg-yellow-100 text-yellow-800 border-yellow-200",
};

function getTopicColor(topic: string): string {
  const key = topic.toLowerCase();
  for (const [k, v] of Object.entries(TOPIC_COLORS)) {
    if (key.includes(k)) return v;
  }
  return "bg-slate-100 text-slate-700 border-slate-200";
}

export default function NewsSummary() {
  const { data: summary, isLoading, isError } = useNewsSummary();

  if (isLoading) {
    return (
      <div className="mb-4 rounded-lg border border-indigo-100 bg-gradient-to-r from-indigo-50 to-purple-50 p-5">
        <div className="flex items-center gap-2 text-sm text-indigo-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating AI summary...
        </div>
      </div>
    );
  }

  if (isError || !summary || !summary.sections?.length) {
    return null;
  }

  return (
    <div className="mb-4 rounded-lg border border-indigo-100 bg-gradient-to-r from-indigo-50 to-purple-50 p-5">
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-indigo-500" />
        <span className="text-sm font-semibold text-indigo-900">
          AI News Brief
        </span>
      </div>

      {/* Overview */}
      {summary.overview && (
        <p className="mb-4 text-sm leading-relaxed text-slate-700">
          {summary.overview}
        </p>
      )}

      {/* Topic sections - grid for alignment */}
      <div className="divide-y divide-indigo-100">
        {summary.sections.map((section) => (
          <div
            key={section.topic}
            className="grid grid-cols-[8rem_1fr] gap-3 py-2.5 first:pt-0 last:pb-0"
          >
            <span
              className={`inline-flex h-fit items-center justify-center rounded-md border px-2 py-1 text-xs font-medium ${getTopicColor(section.topic)}`}
            >
              {section.topic}
            </span>
            <p className="text-sm leading-relaxed text-slate-600">
              {section.summary}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
