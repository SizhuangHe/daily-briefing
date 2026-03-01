import { useQuery } from "@tanstack/react-query";
import { fetchBriefing } from "../api/briefing";

export function useBriefing() {
  return useQuery({
    queryKey: ["briefing"],
    queryFn: fetchBriefing,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
