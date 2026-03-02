import apiClient from "./client";

export interface PreferencesData {
  topics: string[];
  rating_mode: string;
  topic_weights: Record<string, number>;
}

export async function fetchPreferences(): Promise<PreferencesData> {
  const { data } = await apiClient.get<PreferencesData>("/preferences");
  return data;
}

export async function updatePreferences(
  prefs: Partial<Pick<PreferencesData, "topics" | "rating_mode">>
): Promise<PreferencesData> {
  const { data } = await apiClient.put<PreferencesData>("/preferences", prefs);
  return data;
}

export async function fetchAvailableTopics(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>("/preferences/topics");
  return data;
}

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
