import apiClient from "./client";
import type { IndexData, WatchlistItem } from "../types/briefing";

export async function fetchIndices(): Promise<IndexData[]> {
  const { data } = await apiClient.get<IndexData[]>("/stocks/indices");
  return data;
}

export async function fetchWatchlist(): Promise<WatchlistItem[]> {
  const { data } = await apiClient.get<WatchlistItem[]>("/stocks/watchlist");
  return data;
}

export async function addToWatchlist(symbol: string): Promise<WatchlistItem> {
  const { data } = await apiClient.post<WatchlistItem>("/stocks/watchlist", {
    symbol,
  });
  return data;
}

export async function removeFromWatchlist(symbol: string): Promise<void> {
  await apiClient.delete(`/stocks/watchlist/${symbol}`);
}
