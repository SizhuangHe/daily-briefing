import { ExternalLink, Heart, ThumbsDown, ThumbsUp } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useDislikedArticles, useLikedArticles, useRatings, useRateArticle } from "../../hooks/useNews";
import type { Article } from "../../types/briefing";

function RatedArticleCard({
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
            <p className="mt-1 text-sm leading-relaxed text-slate-500">
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
                      {topic}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => onRate(article.id, 1)}
                className={`rounded p-1 transition-colors ${
                  rating === 1
                    ? "bg-emerald-50 text-emerald-600"
                    : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
                }`}
                title="Interested"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => onRate(article.id, -1)}
                className={`rounded p-1 transition-colors ${
                  rating === -1
                    ? "bg-red-50 text-red-500"
                    : "text-slate-300 hover:bg-slate-100 hover:text-slate-500"
                }`}
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

export default function LikedPage() {
  const { data: likedArticles, isLoading: likedLoading } = useLikedArticles();
  const { data: dislikedArticles, isLoading: dislikedLoading } = useDislikedArticles();
  const { data: ratingsMap } = useRatings();
  const rateMutation = useRateArticle();

  const handleRate = (articleId: number, score: number) => {
    const currentRating = ratingsMap?.[articleId] ?? null;
    const newScore = currentRating === score ? 0 : score;
    rateMutation.mutate({ articleId, score: newScore });
  };

  const isLoading = likedLoading || dislikedLoading;

  return (
    <div>
      {/* Liked section */}
      <div className="mb-8">
        <div className="mb-4">
          <div className="flex items-center gap-2">
            <ThumbsUp className="h-5 w-5 text-emerald-500" />
            <h2 className="text-lg font-bold text-slate-900">Liked</h2>
            {likedArticles && (
              <span className="text-sm text-slate-400">({likedArticles.length})</span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Articles you've given a thumbs up.
          </p>
        </div>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-slate-400">
            Loading...
          </div>
        ) : !likedArticles?.length ? (
          <div className="rounded-lg border border-dashed border-slate-200 py-8 text-center">
            <Heart className="mx-auto h-8 w-8 text-slate-300" />
            <p className="mt-2 text-sm text-slate-400">
              No liked articles yet. Use the thumbs up button on news stories to save them here.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {likedArticles.map((article) => (
              <RatedArticleCard
                key={article.id}
                article={article}
                rating={ratingsMap?.[article.id] ?? null}
                onRate={handleRate}
              />
            ))}
          </div>
        )}
      </div>

      {/* Disliked section */}
      <div>
        <div className="mb-4">
          <div className="flex items-center gap-2">
            <ThumbsDown className="h-5 w-5 text-red-400" />
            <h2 className="text-lg font-bold text-slate-900">Disliked</h2>
            {dislikedArticles && (
              <span className="text-sm text-slate-400">({dislikedArticles.length})</span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Articles you've given a thumbs down. These help train your preferences.
          </p>
        </div>

        {isLoading ? (
          <div className="py-8 text-center text-sm text-slate-400">
            Loading...
          </div>
        ) : !dislikedArticles?.length ? (
          <div className="rounded-lg border border-dashed border-slate-200 py-8 text-center">
            <ThumbsDown className="mx-auto h-8 w-8 text-slate-300" />
            <p className="mt-2 text-sm text-slate-400">
              No disliked articles yet.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {dislikedArticles.map((article) => (
              <RatedArticleCard
                key={article.id}
                article={article}
                rating={ratingsMap?.[article.id] ?? null}
                onRate={handleRate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
