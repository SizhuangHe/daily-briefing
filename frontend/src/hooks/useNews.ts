import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDislikedArticles, fetchLikedArticles, fetchNews, fetchNewsSummary, fetchRatings, rateArticle, refreshNews } from "../api/news";

export function useNews(topic?: string) {
  return useQuery({
    queryKey: ["news", topic],
    queryFn: () => fetchNews({ topic, limit: 20 }),
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
    onSuccess: () => {
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
