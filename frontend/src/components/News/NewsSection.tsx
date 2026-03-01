import { useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { useNews, useRefreshNews } from "../../hooks/useNews";
import NewsCard from "./NewsCard";
import NewsSummary from "./NewsSummary";
import TopicFilter from "./TopicFilter";

export default function NewsSection() {
  const [selectedTopic, setSelectedTopic] = useState("all");
  const topic = selectedTopic === "all" ? undefined : selectedTopic;
  const { data: articles, isLoading } = useNews(topic);
  const refreshMutation = useRefreshNews();

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">Top Stories</h3>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
        >
          {refreshMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          {refreshMutation.isPending ? "Fetching..." : "Refresh"}
        </button>
      </div>

      {/* AI Summary */}
      <NewsSummary />

      {/* Topic filters */}
      <div className="mb-4">
        <TopicFilter selected={selectedTopic} onSelect={setSelectedTopic} />
      </div>

      {/* Articles list */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      ) : articles && articles.length > 0 ? (
        <div className="space-y-3">
          {articles.map((article) => (
            <NewsCard key={article.id} article={article} />
          ))}
        </div>
      ) : (
        <p className="py-8 text-center text-sm text-slate-400">
          No articles found. Click Refresh to fetch news.
        </p>
      )}
    </div>
  );
}
