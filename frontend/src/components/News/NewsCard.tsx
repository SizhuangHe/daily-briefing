import { ExternalLink } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { Article } from "../../types/briefing";
import ArticleRating from "./ArticleRating";

interface NewsCardProps {
  article: Article;
}

export default function NewsCard({ article }: NewsCardProps) {
  const timeAgo = article.published_at
    ? formatDistanceToNow(new Date(article.published_at), { addSuffix: true })
    : null;

  return (
    <div className="flex gap-4 rounded-lg border border-slate-200 bg-white p-4 transition-shadow hover:shadow-md">
      {/* Image */}
      {article.image_url && (
        <div className="hidden flex-shrink-0 sm:block">
          <img
            src={article.image_url}
            alt=""
            className="h-20 w-28 rounded-md object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        </div>
      )}

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col justify-between">
        <div>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-1 no-underline"
          >
            <h4 className="text-sm font-semibold leading-snug text-slate-900 group-hover:text-blue-600">
              {article.title}
            </h4>
            <ExternalLink className="mt-0.5 h-3 w-3 flex-shrink-0 text-slate-400 opacity-0 group-hover:opacity-100" />
          </a>

          {/* Gemini summary or description */}
          <p className="mt-1 line-clamp-2 text-xs text-slate-500">
            {article.gemini_summary || article.description || ""}
          </p>
        </div>

        {/* Footer: source, time, topics, rating */}
        <div className="mt-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-400">
              {article.source_name}
            </span>
            {timeAgo && (
              <span className="text-xs text-slate-300">{timeAgo}</span>
            )}
            {article.topics.map((topic) => (
              <span
                key={topic}
                className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium capitalize text-slate-500"
              >
                {topic}
              </span>
            ))}
          </div>
          <ArticleRating articleId={article.id} />
        </div>
      </div>
    </div>
  );
}
