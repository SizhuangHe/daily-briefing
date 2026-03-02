import {
  BarChart3,
  Code2,
  Database,
  History,
  Loader2,
  Target,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import {
  useDevProfile,
  useDevScores,
  useDevMetrics,
  useDevStats,
} from "../../hooks/useDev";
import type { ArticleScoreBreakdown } from "../../api/dev";

function ScoreBar({ value, max = 1, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="h-2 w-full rounded-full bg-slate-100">
      <div
        className={`h-2 rounded-full ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function UserProfileSection() {
  const { data: profile, isLoading } = useDevProfile();

  if (isLoading) {
    return <SectionLoading />;
  }

  if (!profile) return null;

  const sortedTopics = Object.entries(profile.topic_weights).sort(
    ([, a], [, b]) => b - a
  );
  const sortedSources = Object.entries(profile.source_preferences).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-slate-800">User Profile</h3>
        <div className="ml-auto flex items-center gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <ThumbsUp className="h-3 w-3 text-emerald-500" />
            {profile.total_liked}
          </span>
          <span className="flex items-center gap-1">
            <ThumbsDown className="h-3 w-3 text-red-400" />
            {profile.total_disliked}
          </span>
          <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-600">
            {profile.centroid_count} centroid{profile.centroid_count !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Topic Weights */}
      <div className="mb-4">
        <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400">
          Topic Weights
        </h4>
        <div className="space-y-1.5">
          {sortedTopics.map(([topic, weight]) => (
            <div key={topic} className="flex items-center gap-2">
              <span className="w-20 truncate text-xs text-slate-600">
                {topic}
              </span>
              <div className="flex-1">
                <ScoreBar value={weight} max={2.0} color="bg-blue-400" />
              </div>
              <span className="w-10 text-right text-xs tabular-nums text-slate-500">
                {weight.toFixed(2)}
              </span>
            </div>
          ))}
          {sortedTopics.length === 0 && (
            <p className="text-xs text-slate-400">No topic weights yet</p>
          )}
        </div>
      </div>

      {/* Source Preferences */}
      <div>
        <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400">
          Source Preferences
        </h4>
        <div className="space-y-1.5">
          {sortedSources.slice(0, 15).map(([source, weight]) => (
            <div key={source} className="flex items-center gap-2">
              <span className="w-32 truncate text-xs text-slate-600">
                {source}
              </span>
              <div className="flex-1">
                <ScoreBar value={weight} max={1.0} color="bg-emerald-400" />
              </div>
              <span className="w-10 text-right text-xs tabular-nums text-slate-500">
                {weight.toFixed(2)}
              </span>
            </div>
          ))}
          {sortedSources.length === 0 && (
            <p className="text-xs text-slate-400">No source data yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ScoreCell({ value }: { value: number }) {
  const bg =
    value >= 0.7
      ? "bg-emerald-50 text-emerald-700"
      : value >= 0.4
        ? "bg-amber-50 text-amber-700"
        : "bg-slate-50 text-slate-500";
  return (
    <td className={`px-2 py-1.5 text-center text-xs tabular-nums ${bg}`}>
      {value.toFixed(3)}
    </td>
  );
}

function ScoreBreakdownSection() {
  const { data: scores, isLoading } = useDevScores(30);

  if (isLoading) {
    return <SectionLoading />;
  }

  if (!scores?.articles?.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-violet-500" />
          <h3 className="text-sm font-semibold text-slate-800">
            Score Breakdown
          </h3>
        </div>
        <p className="mt-2 text-xs text-slate-400">No scored articles yet</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-violet-500" />
        <h3 className="text-sm font-semibold text-slate-800">
          Score Breakdown
        </h3>
        <span className="text-xs text-slate-400">
          Top {scores.articles.length} articles (72h window)
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wider text-slate-400">
              <th className="px-2 py-2">Title</th>
              <th className="px-2 py-2 text-center">Topic</th>
              <th className="px-2 py-2 text-center">Content</th>
              <th className="px-2 py-2 text-center">Source</th>
              <th className="px-2 py-2 text-center">Recency</th>
              <th className="px-2 py-2 text-center">Final</th>
              <th className="px-2 py-2 text-center">Rating</th>
            </tr>
          </thead>
          <tbody>
            {scores.articles.map((a: ArticleScoreBreakdown) => (
              <tr
                key={a.id}
                className="border-b border-slate-50 hover:bg-slate-50"
              >
                <td className="max-w-[260px] truncate px-2 py-1.5 text-xs text-slate-700">
                  {a.title}
                </td>
                <ScoreCell value={a.raw_scores.topic} />
                <ScoreCell value={a.raw_scores.content} />
                <ScoreCell value={a.raw_scores.source} />
                <ScoreCell value={a.raw_scores.recency} />
                <td className="px-2 py-1.5 text-center text-xs font-semibold tabular-nums text-slate-800">
                  {a.final_score.toFixed(3)}
                </td>
                <td className="px-2 py-1.5 text-center">
                  {a.rating === 1 && (
                    <ThumbsUp className="mx-auto h-3 w-3 text-emerald-500" />
                  )}
                  {a.rating === -1 && (
                    <ThumbsDown className="mx-auto h-3 w-3 text-red-400" />
                  )}
                  {a.rating == null && (
                    <span className="text-xs text-slate-300">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-400">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-slate-800">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{description}</div>
    </div>
  );
}

function EvalMetricsSection() {
  const { data: metrics, isLoading } = useDevMetrics(20);

  if (isLoading) {
    return <SectionLoading />;
  }

  if (!metrics) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Target className="h-4 w-4 text-amber-500" />
        <h3 className="text-sm font-semibold text-slate-800">
          Evaluation Metrics
        </h3>
        <span className="text-xs text-slate-400">k={metrics.k}</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="NDCG@k"
          value={metrics.ndcg_at_k.toFixed(3)}
          description="Ranking quality (liked articles at top)"
        />
        <MetricCard
          label="Like-rate@k"
          value={`${(metrics.like_rate_at_k * 100).toFixed(1)}%`}
          description="Fraction of top-k that were liked"
        />
        <MetricCard
          label="Topic Coverage"
          value={metrics.coverage.topic_entropy.toFixed(2)}
          description={`Shannon entropy (${metrics.coverage.unique_topics} topics)`}
        />
        <MetricCard
          label="Novelty"
          value={`${(metrics.novelty * 100).toFixed(1)}%`}
          description="Topics not in liked history"
        />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-3">
        <MetricCard
          label="Source Coverage"
          value={metrics.coverage.source_entropy.toFixed(2)}
          description={`${metrics.coverage.unique_sources} sources`}
        />
        <MetricCard
          label="Total Liked"
          value={String(metrics.total_liked)}
          description={`of ${metrics.total_rated} rated`}
        />
        <MetricCard
          label="Total Disliked"
          value={String(metrics.total_disliked)}
          description={`of ${metrics.total_rated} rated`}
        />
      </div>
    </div>
  );
}

function RatingHistorySection() {
  const { data: stats, isLoading } = useDevStats();

  if (isLoading) {
    return <SectionLoading />;
  }

  if (!stats?.rating_history?.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-800">
            Rating History
          </h3>
        </div>
        <p className="mt-2 text-xs text-slate-400">No ratings yet</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <History className="h-4 w-4 text-slate-400" />
        <h3 className="text-sm font-semibold text-slate-800">
          Rating History
        </h3>
        <span className="text-xs text-slate-400">Last 20</span>
      </div>
      <div className="space-y-1.5">
        {stats.rating_history.map((r, i) => (
          <div
            key={i}
            className="flex items-center gap-2 rounded px-2 py-1.5 text-xs hover:bg-slate-50"
          >
            {r.score === 1 ? (
              <ThumbsUp className="h-3 w-3 shrink-0 text-emerald-500" />
            ) : (
              <ThumbsDown className="h-3 w-3 shrink-0 text-red-400" />
            )}
            <span className="min-w-0 flex-1 truncate text-slate-700">
              {r.article_title}
            </span>
            <span className="shrink-0 text-slate-400">
              {r.rated_at
                ? formatDistanceToNow(new Date(r.rated_at), {
                    addSuffix: true,
                  })
                : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SystemStatsSection() {
  const { data: stats, isLoading } = useDevStats();

  if (isLoading) {
    return <SectionLoading />;
  }

  if (!stats) return null;

  const statItems = [
    { label: "Total Articles", value: stats.total_articles },
    { label: "With Embeddings", value: stats.articles_with_embeddings },
    {
      label: "Embedding Coverage",
      value:
        stats.total_articles > 0
          ? `${((stats.articles_with_embeddings / stats.total_articles) * 100).toFixed(1)}%`
          : "0%",
    },
    {
      label: "Candidate Window",
      value: `${stats.candidate_window_size} (${stats.candidate_window_hours}h)`,
    },
    { label: "Total Ratings", value: stats.total_ratings },
  ];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Database className="h-4 w-4 text-teal-500" />
        <h3 className="text-sm font-semibold text-slate-800">System Stats</h3>
      </div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
        {statItems.map((item) => (
          <div key={item.label}>
            <div className="text-xs text-slate-400">{item.label}</div>
            <div className="text-sm font-semibold text-slate-800">
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionLoading() {
  return (
    <div className="flex items-center justify-center rounded-lg border border-slate-200 bg-white py-8 shadow-sm">
      <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
    </div>
  );
}

export default function DevPage() {
  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <Code2 className="h-5 w-5 text-violet-500" />
          <h2 className="text-lg font-bold text-slate-900">
            Developer Dashboard
          </h2>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Recommendation engine introspection and evaluation metrics.
        </p>
      </div>

      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <UserProfileSection />
          <EvalMetricsSection />
        </div>
        <ScoreBreakdownSection />
        <div className="grid gap-4 lg:grid-cols-2">
          <RatingHistorySection />
          <SystemStatsSection />
        </div>
      </div>
    </div>
  );
}
