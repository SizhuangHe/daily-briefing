import { CalendarDays, ListTodo, Loader2, Sparkles } from "lucide-react";
import { useCalendarSummary } from "../../hooks/useCalendar";
import EventCard from "./EventCard";
import ReminderCard from "./ReminderCard";

export default function CalendarSection() {
  const { data, isLoading, isError, error } = useCalendarSummary();

  const isPermissionError =
    isError && (error as { response?: { status?: number } })?.response?.status === 403;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="mb-4 text-lg font-semibold text-slate-900">
        Today's Schedule
      </h3>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      ) : isPermissionError ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-medium">Calendar access required</p>
          <p className="mt-1 text-amber-700">
            Go to System Settings &gt; Privacy &amp; Security &gt; Automation
            and enable Calendar/Reminders access for Terminal.
          </p>
        </div>
      ) : !data ? (
        <p className="py-4 text-center text-sm text-slate-400">
          Unable to load calendar data.
        </p>
      ) : (
        <div className="space-y-5">
          {/* AI Summary */}
          {data.summary && (
            <div className="rounded-lg border border-indigo-100 bg-gradient-to-r from-indigo-50 to-purple-50 p-4">
              <div className="mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-indigo-500" />
                <span className="text-sm font-semibold text-indigo-900">
                  Schedule Summary
                </span>
              </div>
              <p className="text-sm leading-relaxed text-slate-700">
                {data.summary}
              </p>
            </div>
          )}

          {/* Events */}
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
              <CalendarDays className="h-4 w-4" />
              Events
              <span className="text-xs text-slate-400">
                ({data.events.length})
              </span>
            </div>
            {data.events.length > 0 ? (
              <div className="space-y-2">
                {data.events.map((event, i) => (
                  <EventCard key={`${event.title}-${i}`} event={event} />
                ))}
              </div>
            ) : (
              <p className="py-2 text-sm text-slate-400">
                No events scheduled for today.
              </p>
            )}
          </div>

          {/* Reminders */}
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
              <ListTodo className="h-4 w-4" />
              Reminders
              <span className="text-xs text-slate-400">
                ({data.reminders.length})
              </span>
            </div>
            {data.reminders.length > 0 ? (
              <div className="space-y-2">
                {data.reminders.map((reminder, i) => (
                  <ReminderCard
                    key={`${reminder.title}-${i}`}
                    reminder={reminder}
                  />
                ))}
              </div>
            ) : (
              <p className="py-2 text-sm text-slate-400">
                No pending reminders.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
