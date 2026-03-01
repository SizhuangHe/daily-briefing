import { ThumbsUp, ThumbsDown } from "lucide-react";
import { clsx } from "clsx";
import { useRateArticle } from "../../hooks/useNews";

interface ArticleRatingProps {
  articleId: number;
  currentRating?: number;
}

export default function ArticleRating({
  articleId,
  currentRating,
}: ArticleRatingProps) {
  const rateMutation = useRateArticle();

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={(e) => {
          e.stopPropagation();
          rateMutation.mutate({ articleId, score: 1 });
        }}
        className={clsx(
          "rounded p-1 transition-colors",
          currentRating === 1
            ? "bg-emerald-100 text-emerald-600"
            : "text-slate-400 hover:bg-emerald-50 hover:text-emerald-500"
        )}
        title="Thumbs up"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          rateMutation.mutate({ articleId, score: -1 });
        }}
        className={clsx(
          "rounded p-1 transition-colors",
          currentRating === -1
            ? "bg-red-100 text-red-600"
            : "text-slate-400 hover:bg-red-50 hover:text-red-500"
        )}
        title="Thumbs down"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
