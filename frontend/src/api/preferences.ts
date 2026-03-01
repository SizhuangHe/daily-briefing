import apiClient from "./client";

export interface NewsSourceData {
  id: number;
  name: string;
  url: string;
  source_type: string;
  enabled: boolean;
}

export async function fetchSources(): Promise<NewsSourceData[]> {
  const { data } = await apiClient.get<NewsSourceData[]>(
    "/preferences/sources"
  );
  return data;
}

export async function addSource(
  source: Omit<NewsSourceData, "id" | "enabled">
): Promise<NewsSourceData> {
  const { data } = await apiClient.post<NewsSourceData>(
    "/preferences/sources",
    source
  );
  return data;
}

export async function toggleSource(
  sourceId: number
): Promise<{ id: number; enabled: boolean }> {
  const { data } = await apiClient.put(`/preferences/sources/${sourceId}`);
  return data;
}

export async function deleteSource(sourceId: number): Promise<void> {
  await apiClient.delete(`/preferences/sources/${sourceId}`);
}
