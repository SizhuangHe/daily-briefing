import apiClient from "./client";

export interface DevProfile {
  topic_weights: Record<string, number>;
  source_preferences: Record<string, number>;
  centroid_count: number;
  selected_topics: string[];
  total_liked: number;
  total_disliked: number;
}

export interface ArticleScoreBreakdown {
  id: number;
  title: string;
  source_name?: string;
  topics: string[];
  final_score: number;
  raw_scores: {
    topic: number;
    content: number;
    source: number;
    recency: number;
  };
  rating?: number;
  published_at?: string;
}

export interface DevScores {
  articles: ArticleScoreBreakdown[];
}

export interface CoverageMetrics {
  topic_entropy: number;
  source_entropy: number;
  unique_topics: number;
  unique_sources: number;
}

export interface DevMetrics {
  k: number;
  ndcg_at_k: number;
  like_rate_at_k: number;
  coverage: CoverageMetrics;
  novelty: number;
  total_rated: number;
  total_liked: number;
  total_disliked: number;
}

export interface RatingHistoryEntry {
  article_id: number;
  article_title: string;
  score: number;
  rated_at: string;
}

export interface DevStats {
  total_articles: number;
  articles_with_embeddings: number;
  total_ratings: number;
  candidate_window_size: number;
  candidate_window_hours: number;
  rating_history: RatingHistoryEntry[];
}

export async function fetchDevProfile(): Promise<DevProfile> {
  const { data } = await apiClient.get<DevProfile>("/dev/profile");
  return data;
}

export async function fetchDevScores(limit?: number): Promise<DevScores> {
  const { data } = await apiClient.get<DevScores>("/dev/scores", {
    params: { limit: limit || 30 },
  });
  return data;
}

export async function fetchDevMetrics(k?: number): Promise<DevMetrics> {
  const { data } = await apiClient.get<DevMetrics>("/dev/metrics", {
    params: { k: k || 20 },
  });
  return data;
}

export async function fetchDevStats(): Promise<DevStats> {
  const { data } = await apiClient.get<DevStats>("/dev/stats");
  return data;
}
