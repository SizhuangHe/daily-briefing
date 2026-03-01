import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTodayInspiration, refreshInspiration } from "../api/inspiration";

export function useInspiration() {
  return useQuery({
    queryKey: ["inspiration"],
    queryFn: fetchTodayInspiration,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

export function useRefreshInspiration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: refreshInspiration,
    onSuccess: (data) => {
      queryClient.setQueryData(["inspiration"], data);
    },
  });
}
