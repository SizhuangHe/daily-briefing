import apiClient from "./client";
import type { CalendarEvent, ReminderItem } from "../types/briefing";

export interface CalendarSummaryResponse {
  events: CalendarEvent[];
  reminders: ReminderItem[];
  summary: string;
}

export async function fetchCalendarSummary(): Promise<CalendarSummaryResponse> {
  const { data } = await apiClient.get<CalendarSummaryResponse>(
    "/calendar/summary"
  );
  return data;
}

export async function fetchCalendarEvents(): Promise<CalendarEvent[]> {
  const { data } = await apiClient.get<CalendarEvent[]>("/calendar/events");
  return data;
}

export async function fetchReminders(): Promise<ReminderItem[]> {
  const { data } = await apiClient.get<ReminderItem[]>("/calendar/reminders");
  return data;
}
