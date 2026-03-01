import { format } from "date-fns";
import CalendarSection from "../Calendar/CalendarSection";
import StocksSection from "../Stocks/StocksSection";
import NewsSection from "../News/NewsSection";

export default function DashboardPage() {
  const today = format(new Date(), "EEEE, MMMM d, yyyy");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Good Morning</h2>
        <p className="text-sm text-slate-500">{today}</p>
      </div>

      {/* Grid layout for sections */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Calendar & Schedule Summary */}
        <div className="lg:col-span-2">
          <CalendarSection />
        </div>

        {/* Stock Market */}
        <div className="lg:col-span-2">
          <StocksSection />
        </div>

        {/* News */}
        <div className="lg:col-span-2">
          <NewsSection />
        </div>

        {/* Inspiration */}
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">
            Daily Inspiration
          </h3>
          <p className="text-sm text-slate-400">
            Inspiration content coming in Phase 6...
          </p>
        </div>
      </div>
    </div>
  );
}
