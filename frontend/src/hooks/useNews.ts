import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDislikedArticles, fetchLikedArticles, fetchNews, fetchNewsSummary, fetchRatings, fetchSources, rateArticle, refreshNews } from "../api/news";

export function useNews(params?: {
  topic?: string;
  source?: string;
  sort?: string;
  limit?: number;
}) {
  const { topic, source, sort, limit = 20 } = params ?? {};
  return useQuery({
    queryKey: ["news", topic, source, sort, limit],
    queryFn: () => fetchNews({ topic, source, sort, limit }),
  });
}

export function useNewsSources() {
  return useQuery({
    queryKey: ["news-sources"],
    queryFn: fetchSources,
  });
}

export function useNewsSummary() {
  return useQuery({
    queryKey: ["news-summary"],
    queryFn: fetchNewsSummary,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useRatings() {
  return useQuery({
    queryKey: ["ratings"],
    queryFn: fetchRatings,
  });
}

export function useLikedArticles() {
  return useQuery({
    queryKey: ["liked"],
    queryFn: fetchLikedArticles,
  });
}

export function useDislikedArticles() {
  return useQuery({
    queryKey: ["disliked"],
    queryFn: fetchDislikedArticles,
  });
}

export function useRateArticle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ articleId, score }: { articleId: number; score: number }) =>
      rateArticle(articleId, score),
    onMutate: async ({ articleId, score }) => {
      // Optimistic update: immediately reflect the new rating in the cache
      await queryClient.cancelQueries({ queryKey: ["ratings"] });
      const prev = queryClient.getQueryData<Record<number, number>>(["ratings"]);
      queryClient.setQueryData<Record<number, number>>(["ratings"], (old) => {
        const next = { ...old };
        if (score === 0) {
          delete next[articleId];
        } else {
          next[articleId] = score;
        }
        return next;
      });
      return { prev };
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) {
        queryClient.setQueryData(["ratings"], context.prev);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["news"] });
      queryClient.invalidateQueries({ queryKey: ["ratings"] });
      queryClient.invalidateQueries({ queryKey: ["liked"] });
      queryClient.invalidateQueries({ queryKey: ["disliked"] });
    },
  });
}


export function useRefreshNews() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: refreshNews,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["news"] });
      queryClient.invalidateQueries({ queryKey: ["news-summary"] });
      queryClient.invalidateQueries({ queryKey: ["briefing"] });
    },
  });
}
