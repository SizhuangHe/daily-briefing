import { useQuery } from "@tanstack/react-query";
import { fetchCalendarSummary } from "../api/calendar";

export function useCalendarSummary() {
  return useQuery({
    queryKey: ["calendar-summary"],
    queryFn: fetchCalendarSummary,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry on permission errors
  });
}
