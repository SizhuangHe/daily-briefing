import apiClient from "./client";
import type { BriefingResponse } from "../types/briefing";

export async function fetchBriefing(): Promise<BriefingResponse> {
  const { data } = await apiClient.get<BriefingResponse>("/briefing");
  return data;
}
