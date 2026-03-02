import { Loader2 } from "lucide-react";
import {
  useAvailableTopics,
  usePreferences,
  useUpdatePreferences,
} from "../../hooks/usePreferences";

const TOPIC_LABELS: Record<string, string> = {
  disaster: "Disaster",
  public_safety: "Public Safety",
  health: "Health",
  weather: "Weather",
  infrastructure: "Infrastructure",
  war_conflict: "Conflict",
  policy: "Policy",
  financial_shock: "Financial",
  market: "Markets",
  tech: "Technology",
  science: "Science",
  crime: "Crime",
  diplomacy: "Diplomacy",
  sports: "Sports",
  entertainment: "Entertainment",
  ai: "AI",
  business: "Business",
  energy: "Energy",
  environment: "Environment",
  education: "Education",
  space: "Space",
  automotive: "Automotive",
  crypto: "Crypto",
};

function label(topic: string): string {
  return TOPIC_LABELS[topic] || topic.charAt(0).toUpperCase() + topic.slice(1);
}

export default function TopicSelector() {
  const { data: available, isLoading: loadingTopics } = useAvailableTopics();
  const { data: prefs, isLoading: loadingPrefs } = usePreferences();
  const updateMutation = useUpdatePreferences();

  const selected = new Set(prefs?.topics || []);

  const toggle = (topic: string) => {
    const next = new Set(selected);
    if (next.has(topic)) next.delete(topic);
    else next.add(topic);
    updateMutation.mutate({ topics: [...next] });
  };

  if (loadingTopics || loadingPrefs) {
    return (
      <div className="flex justify-center py-4">
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div>
      <p className="mb-3 text-sm text-slate-500">
        Select topics you're interested in. This helps personalize your
        briefing.
        {selected.size === 0 &&
          " No topics selected — all topics weighted equally."}
      </p>
      <div className="flex flex-wrap gap-2">
        {available?.map((topic) => (
          <button
            key={topic}
            onClick={() => toggle(topic)}
            className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors ${
              selected.has(topic)
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {label(topic)}
          </button>
        ))}
      </div>
    </div>
  );
}
