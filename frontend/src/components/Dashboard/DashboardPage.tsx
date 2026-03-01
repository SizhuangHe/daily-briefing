import { format } from "date-fns";
import BriefingView from "../Briefing/BriefingView";
import CalendarSection from "../Calendar/CalendarSection";
import InspirationSection from "../Inspiration/InspirationSection";
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

        {/* Daily Briefing (Must-Know + Interest channels) */}
        <div className="lg:col-span-2">
          <BriefingView />
        </div>

        {/* All News (browse/filter) */}
        <div className="lg:col-span-2">
          <NewsSection />
        </div>

        {/* Inspiration */}
        <div className="lg:col-span-2">
          <InspirationSection />
        </div>
      </div>
    </div>
  );
}
