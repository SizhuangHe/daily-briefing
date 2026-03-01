import { CheckCircle2 } from "lucide-react";
import type { ReminderItem } from "../../types/briefing";

const PRIORITY_STYLES: Record<number, string> = {
  0: "border-slate-200",
  1: "border-red-300 bg-red-50/50",
  5: "border-orange-300 bg-orange-50/50",
  9: "border-blue-200",
};

function getPriorityStyle(priority: number): string {
  if (priority >= 1 && priority <= 4) return PRIORITY_STYLES[1];
  if (priority >= 5 && priority <= 6) return PRIORITY_STYLES[5];
  if (priority >= 7 && priority <= 9) return PRIORITY_STYLES[9];
  return PRIORITY_STYLES[0];
}

function getPriorityLabel(priority: number): string | null {
  if (priority >= 1 && priority <= 4) return "High";
  if (priority >= 5 && priority <= 6) return "Medium";
  if (priority >= 7 && priority <= 9) return "Low";
  return null;
}

export default function ReminderCard({
  reminder,
}: {
  reminder: ReminderItem;
}) {
  const priorityLabel = getPriorityLabel(reminder.priority);

  return (
    <div
      className={`flex items-start gap-3 rounded-md border px-3 py-2.5 ${getPriorityStyle(reminder.priority)}`}
    >
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-800">{reminder.title}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500">
          {reminder.due_date && (
            <span>
              Due:{" "}
              {new Date(reminder.due_date).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              })}
            </span>
          )}
          {priorityLabel && (
            <span className="rounded bg-slate-200 px-1.5 py-0.5 text-slate-600">
              {priorityLabel}
            </span>
          )}
          {reminder.list_name && (
            <span className="text-slate-400">{reminder.list_name}</span>
          )}
        </div>
        {reminder.notes && (
          <p className="mt-1 text-xs text-slate-400 line-clamp-2">
            {reminder.notes}
          </p>
        )}
      </div>
    </div>
  );
}
