import apiClient from "./client";
import type { Article, NewsSummary } from "../types/briefing";

export async function fetchNews(params?: {
  topic?: string;
  limit?: number;
  offset?: number;
}): Promise<Article[]> {
  const { data } = await apiClient.get<Article[]>("/news", { params });
  return data;
}

export async function rateArticle(
  articleId: number,
  score: number
): Promise<void> {
  await apiClient.post(`/news/${articleId}/rate`, { score });
}

export async function fetchNewsSummary(): Promise<NewsSummary> {
  const { data } = await apiClient.get<NewsSummary>("/news/summary");
  return data;
}

export async function refreshNews(): Promise<{
  new_articles: number;
  summaries_generated: number;
}> {
  const { data } = await apiClient.post("/news/refresh");
  return data;
}
