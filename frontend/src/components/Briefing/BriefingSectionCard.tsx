import { BookOpen, CircleDot, Sparkles } from "lucide-react";
import type { BriefingSection } from "../../types/briefing";
import StoryCard from "./StoryCard";

const SECTION_CONFIG: Record<
  string,
  {
    icon: typeof CircleDot;
    iconColor: string;
    borderColor: string;
    bgColor: string;
    variant: "urgent" | "affects_you" | "normal";
  }
> = {
  Urgent: {
    icon: CircleDot,
    iconColor: "text-slate-600",
    borderColor: "border-slate-200",
    bgColor: "bg-white",
    variant: "urgent",
  },
  "Affects You": {
    icon: BookOpen,
    iconColor: "text-slate-500",
    borderColor: "border-slate-200",
    bgColor: "bg-white",
    variant: "affects_you",
  },
  "Your Interests": {
    icon: Sparkles,
    iconColor: "text-blue-500",
    borderColor: "border-slate-200",
    bgColor: "bg-white",
    variant: "normal",
  },
};

export default function BriefingSectionCard({
  section,
}: {
  section: BriefingSection;
}) {
  const config = SECTION_CONFIG[section.title] || SECTION_CONFIG["Your Interests"];
  const Icon = config.icon;

  if (!section.stories.length) return null;

  return (
    <div
      className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-5 shadow-sm`}
    >
      {/* Header */}
      <div className="mb-1 flex items-center gap-2">
        <Icon className={`h-4 w-4 ${config.iconColor}`} />
        <h3 className="text-sm font-semibold text-slate-900">
          {section.title}
        </h3>
        <span className="text-xs text-slate-400">
          ({section.stories.length})
        </span>
      </div>
      <p className="mb-3 text-xs text-slate-500">{section.description}</p>

      {/* Stories */}
      <div className="space-y-2">
        {section.stories.map((story, i) => (
          <StoryCard
            key={`${story.headline}-${i}`}
            story={story}
            variant={config.variant}
          />
        ))}
      </div>
    </div>
  );
}
