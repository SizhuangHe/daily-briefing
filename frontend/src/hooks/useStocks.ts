import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchIndices,
  fetchWatchlist,
  addToWatchlist,
  removeFromWatchlist,
} from "../api/stocks";

export function useIndices() {
  return useQuery({
    queryKey: ["stocks", "indices"],
    queryFn: fetchIndices,
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

export function useWatchlist() {
  return useQuery({
    queryKey: ["stocks", "watchlist"],
    queryFn: fetchWatchlist,
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: addToWatchlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks", "watchlist"] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stocks", "watchlist"] });
    },
  });
}
