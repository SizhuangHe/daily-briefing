import { useQuery } from "@tanstack/react-query";
import {
  fetchDevMetrics,
  fetchDevProfile,
  fetchDevScores,
  fetchDevStats,
} from "../api/dev";

export function useDevProfile() {
  return useQuery({
    queryKey: ["dev-profile"],
    queryFn: fetchDevProfile,
    staleTime: 30 * 1000,
  });
}

export function useDevScores(limit?: number) {
  return useQuery({
    queryKey: ["dev-scores", limit],
    queryFn: () => fetchDevScores(limit),
    staleTime: 30 * 1000,
  });
}

export function useDevMetrics(k?: number) {
  return useQuery({
    queryKey: ["dev-metrics", k],
    queryFn: () => fetchDevMetrics(k),
    staleTime: 60 * 1000,
  });
}

export function useDevStats() {
  return useQuery({
    queryKey: ["dev-stats"],
    queryFn: fetchDevStats,
    staleTime: 30 * 1000,
  });
}
