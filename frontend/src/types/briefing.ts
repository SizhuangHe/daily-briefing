export interface Article {
  id: number;
  title: string;
  description?: string;
  url: string;
  source_name?: string;
  image_url?: string;
  topics: string[];
  gemini_summary?: string;
  recommendation_score: number;
  published_at?: string;
}

export interface BriefArticle {
  id: number;
  title: string;
  description?: string;
  url: string;
  source_name?: string;
  image_url?: string;
  topics: string[];
  gemini_summary?: string;
  event_type?: string;
  severity?: string;
  time_sensitivity?: string;
  geo_scope?: string;
  personal_impact_flags: string[];
  why_it_matters?: string;
  must_know_level: string;
  importance_score: number;
  interest_score: number;
  confirmed_sources: number;
  published_at?: string;
}

export interface BriefingSection {
  title: string;
  description: string;
  articles: BriefArticle[];
}

export interface BriefingResponse {
  date: string;
  urgent: BriefingSection;
  affects_you: BriefingSection;
  interests: BriefingSection;
  overview: string;
}

export interface IndexData {
  name: string;
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
}

export interface WatchlistItem {
  symbol: string;
  name?: string;
  price?: number;
  change?: number;
  change_percent?: number;
}

export interface CalendarEvent {
  title: string;
  start_time?: string;
  end_time?: string;
  location?: string;
  calendar?: string;
}

export interface ReminderItem {
  title: string;
  due_date?: string;
  notes?: string;
  priority: number;
  list_name?: string;
}

export interface Quote {
  text: string;
  author?: string;
}

export interface Inspiration {
  quote?: Quote;
  fun_fact?: string;
  activity?: string;
}

export interface NewsSummarySection {
  topic: string;
  summary: string;
}

export interface NewsSummary {
  overview: string;
  sections: NewsSummarySection[];
}

export interface Briefing {
  date: string;
  news: Article[];
  stocks: {
    indices: IndexData[];
    watchlist: WatchlistItem[];
  };
  calendar: {
    events: CalendarEvent[];
    reminders: ReminderItem[];
    summary: string;
  };
  inspiration: Inspiration;
}
