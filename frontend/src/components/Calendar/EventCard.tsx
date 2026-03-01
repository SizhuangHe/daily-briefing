import { Clock, MapPin } from "lucide-react";
import type { CalendarEvent } from "../../types/briefing";

function formatTime(dateStr?: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export default function EventCard({ event }: { event: CalendarEvent }) {
  const startTime = formatTime(event.start_time);
  const endTime = formatTime(event.end_time);
  const timeRange =
    startTime && endTime ? `${startTime} – ${endTime}` : startTime || "";

  return (
    <div className="flex items-start gap-3 rounded-md border border-slate-100 bg-slate-50 px-3 py-2.5">
      <div className="mt-0.5 rounded bg-blue-100 p-1.5">
        <Clock className="h-3.5 w-3.5 text-blue-600" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-800">{event.title}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-slate-500">
          {timeRange && <span>{timeRange}</span>}
          {event.location && (
            <span className="flex items-center gap-0.5">
              <MapPin className="h-3 w-3" />
              {event.location}
            </span>
          )}
          {event.calendar && (
            <span className="rounded bg-slate-200 px-1.5 py-0.5 text-slate-600">
              {event.calendar}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
