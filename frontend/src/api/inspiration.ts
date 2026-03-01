import apiClient from "./client";
import type { Inspiration } from "../types/briefing";

export async function fetchTodayInspiration(): Promise<Inspiration> {
  const { data } = await apiClient.get<Inspiration>("/inspiration/today");
  return data;
}

export async function refreshInspiration(): Promise<Inspiration> {
  const { data } = await apiClient.post<Inspiration>("/inspiration/refresh");
  return data;
}
