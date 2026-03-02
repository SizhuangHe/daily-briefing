import { useQuery } from "@tanstack/react-query";
import { fetchBriefing } from "../api/briefing";

export function useBriefing() {
  return useQuery({
    queryKey: ["briefing"],
    queryFn: fetchBriefing,
    staleTime: 30 * 60 * 1000, // 30 minutes — backend caches & checks for new articles
  });
}
