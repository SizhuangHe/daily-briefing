import { TrendingUp, TrendingDown } from "lucide-react";
import { clsx } from "clsx";
import type { IndexData } from "../../types/briefing";

interface IndexCardProps {
  index: IndexData;
}

export default function IndexCard({ index }: IndexCardProps) {
  const isPositive = index.change >= 0;

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div>
        <p className="text-sm font-medium text-slate-500">{index.name}</p>
        <p className="text-lg font-bold text-slate-900">
          {index.price.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </p>
      </div>
      <div
        className={clsx(
          "flex items-center gap-1 rounded-md px-2 py-1 text-sm font-semibold",
          isPositive
            ? "bg-emerald-50 text-emerald-700"
            : "bg-red-50 text-red-700"
        )}
      >
        {isPositive ? (
          <TrendingUp className="h-4 w-4" />
        ) : (
          <TrendingDown className="h-4 w-4" />
        )}
        <span>
          {isPositive ? "+" : ""}
          {index.change.toFixed(2)} ({isPositive ? "+" : ""}
          {index.change_percent.toFixed(2)}%)
        </span>
      </div>
    </div>
  );
}
