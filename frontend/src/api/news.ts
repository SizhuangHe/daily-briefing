import apiClient from "./client";
import type { Article, NewsSummary } from "../types/briefing";

export async function fetchNews(params?: {
  topic?: string;
  source?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<Article[]> {
  const { data } = await apiClient.get<Article[]>("/news", { params });
  return data;
}

export async function fetchSources(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>("/news/sources");
  return data;
}

export async function fetchRatings(): Promise<Record<number, number>> {
  const { data } = await apiClient.get<Record<number, number>>("/news/ratings");
  return data;
}

export async function rateArticle(
  articleId: number,
  score: number
): Promise<void> {
  await apiClient.post(`/news/${articleId}/rate`, { score });
}


export async function fetchLikedArticles(): Promise<Article[]> {
  const { data } = await apiClient.get<Article[]>("/news/liked");
  return data;
}

export async function fetchDislikedArticles(): Promise<Article[]> {
  const { data } = await apiClient.get<Article[]>("/news/disliked");
  return data;
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
