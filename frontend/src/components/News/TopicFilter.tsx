import { clsx } from "clsx";

const TOPICS = ["all", "ai", "tech", "finance", "science", "world", "general"];

interface TopicFilterProps {
  selected: string;
  onSelect: (topic: string) => void;
}

export default function TopicFilter({ selected, onSelect }: TopicFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {TOPICS.map((topic) => (
        <button
          key={topic}
          onClick={() => onSelect(topic)}
          className={clsx(
            "rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors",
            selected === topic
              ? "bg-blue-600 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          )}
        >
          {topic}
        </button>
      ))}
    </div>
  );
}
