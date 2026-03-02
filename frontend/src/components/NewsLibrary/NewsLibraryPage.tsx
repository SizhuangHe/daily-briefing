import { useState } from "react";
import {
  ExternalLink,
  Filter,
  Library,
  Loader2,
  Newspaper,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { clsx } from "clsx";
import {
  useNews,
  useNewsSources,
  useRatings,
  useRateArticle,
} from "../../hooks/useNews";
import { useAvailableTopics } from "../../hooks/usePreferences";
import type { Article } from "../../types/briefing";

const TOPIC_LABELS: Record<string, string> = {
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
  ai: "AI",
  business: "Business",
  energy: "Energy",
  environment: "Environment",
  education: "Education",
  space: "Space",
  automotive: "Automotive",
  crypto: "Crypto",
};

function topicLabel(topic: string): string {
  return TOPIC_LABELS[topic] || topic.charAt(0).toUpperCase() + topic.slice(1);
}

function ArticleCard({
  article,
  rating,
  onRate,
}: {
  article: Article;
  rating: number | null;
  onRate: (articleId: number, score: number) => void;
}) {
  const timeAgo = article.published_at
    ? formatDistanceToNow(new Date(article.published_at), { addSuffix: true })
    : null;

  return (
    <div className="group rounded-lg border border-slate-100 bg-white px-4 py-3 transition-colors hover:border-slate-200">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-start gap-1.5 no-underline"
          >
            <h4 className="text-sm font-semibold text-slate-800 group-hover:text-blue-600">
              {article.title}
            </h4>
            <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-300 opacity-0 transition-opacity group-hover:opacity-100" />
          </a>
          {article.gemini_summary && (
            <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-slate-500">
              {article.gemini_summary}
            </p>
          )}
          {!article.gemini_summary && article.description && (
            <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-slate-500">
              {article.description}
            </p>
          )}
          <div className="mt-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              {article.source_name && (
                <span className="font-medium text-slate-500">
                  {article.source_name}
                </span>
              )}
              {timeAgo && <span>{timeAgo}</span>}
              {article.topics.length > 0 && (
                <div className="flex gap-1">
                  {article.topics.slice(0, 3).map((topic) => (
                    <span
                      key={topic}
                      className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500"
                    >
                      {topicLabel(topic)}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => onRate(article.id, 1)}
                className={clsx(
                  "rounded p-1 transition-colors",
                  rating === 1
                    ? "bg-emerald-50 text-emerald-600"
                    : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
                )}
                title="Interested"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => onRate(article.id, -1)}
                className={clsx(
                  "rounded p-1 transition-colors",
                  rating === -1
                    ? "bg-red-50 text-red-500"
                    : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
                )}
                title="Not interested"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NewsLibraryPage() {
  const [selectedTopic, setSelectedTopic] = useState<string | undefined>(
    undefined
  );
  const [selectedSource, setSelectedSource] = useState<string | undefined>(
    undefined
  );
  const [unratedOnly, setUnratedOnly] = useState(false);

  const { data: topics, isLoading: topicsLoading } = useAvailableTopics();
  const { data: sources } = useNewsSources();
  const { data: articles, isLoading: articlesLoading } = useNews({
    topic: selectedTopic,
    source: selectedSource,
    sort: "time",
    limit: 500,
  });
  const { data: ratingsMap } = useRatings();
  const rateMutation = useRateArticle();

  const handleRate = (articleId: number, score: number) => {
    const currentRating = ratingsMap?.[articleId] ?? null;
    const newScore = currentRating === score ? 0 : score;
    rateMutation.mutate({ articleId, score: newScore });
  };

  // Client-side filter for unrated
  const filteredArticles = articles?.filter((a) => {
    if (unratedOnly && ratingsMap?.[a.id] != null) return false;
    return true;
  });

  const totalCount = articles?.length ?? 0;
  const ratedCount = articles
    ? articles.filter((a) => ratingsMap?.[a.id] != null).length
    : 0;
  const unratedCount = totalCount - ratedCount;

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <Library className="h-5 w-5 text-blue-500" />
          <h2 className="text-lg font-bold text-slate-900">News Library</h2>
          {articles && (
            <span className="text-sm text-slate-400">
              {unratedOnly
                ? `${filteredArticles?.length ?? 0} unrated`
                : `${totalCount} articles`}
              {!unratedOnly && unratedCount > 0 && (
                <span className="ml-1 text-amber-500">
                  ({unratedCount} unrated)
                </span>
              )}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Browse and rate articles by topic to train your recommendations.
        </p>
      </div>

      {/* Topic filter bar */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        <button
          onClick={() => setSelectedTopic(undefined)}
          className={clsx(
            "rounded-full px-3 py-1 text-xs font-medium transition-colors",
            selectedTopic === undefined
              ? "bg-blue-600 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          )}
        >
          All Topics
        </button>
        {topicsLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
        ) : (
          topics?.map((topic) => (
            <button
              key={topic}
              onClick={() => setSelectedTopic(topic)}
              className={clsx(
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                selectedTopic === topic
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              )}
            >
              {topicLabel(topic)}
            </button>
          ))
        )}
      </div>

      {/* Source filter + unrated toggle */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Filter className="h-3.5 w-3.5 text-slate-400" />
          <select
            value={selectedSource ?? ""}
            onChange={(e) => setSelectedSource(e.target.value || undefined)}
            className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 focus:border-blue-400 focus:outline-none"
          >
            <option value="">All Sources</option>
            {sources?.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <label className="flex cursor-pointer items-center gap-1.5 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={unratedOnly}
            onChange={(e) => setUnratedOnly(e.target.checked)}
            className="rounded border-slate-300"
          />
          Unrated only
        </label>
      </div>

      {/* Article list */}
      {articlesLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        </div>
      ) : !filteredArticles?.length ? (
        <div className="rounded-lg border border-dashed border-slate-200 py-12 text-center">
          <Newspaper className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-2 text-sm text-slate-400">
            {unratedOnly
              ? "All articles have been rated!"
              : `No articles found${selectedTopic ? ` for "${topicLabel(selectedTopic)}"` : ""}.`}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredArticles.map((article) => (
            <ArticleCard
              key={article.id}
              article={article}
              rating={ratingsMap?.[article.id] ?? null}
              onRate={handleRate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
