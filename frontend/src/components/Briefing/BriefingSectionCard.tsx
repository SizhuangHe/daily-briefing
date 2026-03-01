import { AlertTriangle, Shield, Sparkles } from "lucide-react";
import type { BriefingSection } from "../../types/briefing";
import BriefArticleCard from "./BriefArticleCard";

const SECTION_CONFIG: Record<
  string,
  {
    icon: typeof AlertTriangle;
    iconColor: string;
    borderColor: string;
    bgGradient: string;
    variant: "urgent" | "affects_you" | "normal";
  }
> = {
  Urgent: {
    icon: AlertTriangle,
    iconColor: "text-red-500",
    borderColor: "border-red-200",
    bgGradient: "from-red-50 to-orange-50",
    variant: "urgent",
  },
  "Affects You": {
    icon: Shield,
    iconColor: "text-orange-500",
    borderColor: "border-orange-200",
    bgGradient: "from-orange-50 to-amber-50",
    variant: "affects_you",
  },
  "Your Interests": {
    icon: Sparkles,
    iconColor: "text-blue-500",
    borderColor: "border-blue-100",
    bgGradient: "from-blue-50 to-indigo-50",
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

  if (!section.articles.length) return null;

  return (
    <div
      className={`rounded-lg border ${config.borderColor} bg-gradient-to-r ${config.bgGradient} p-5`}
    >
      {/* Header */}
      <div className="mb-1 flex items-center gap-2">
        <Icon className={`h-4 w-4 ${config.iconColor}`} />
        <h3 className="text-sm font-semibold text-slate-900">
          {section.title}
        </h3>
        <span className="text-xs text-slate-400">
          ({section.articles.length})
        </span>
      </div>
      <p className="mb-3 text-xs text-slate-500">{section.description}</p>

      {/* Articles */}
      <div className="space-y-2">
        {section.articles.map((article) => (
          <BriefArticleCard
            key={article.id}
            article={article}
            variant={config.variant}
          />
        ))}
      </div>
    </div>
  );
}
