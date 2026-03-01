import { Link, useLocation } from "react-router-dom";
import { Newspaper, Settings } from "lucide-react";
import { clsx } from "clsx";

export default function Header() {
  const location = useLocation();

  return (
    <header className="border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <Newspaper className="h-6 w-6 text-blue-600" />
          <h1 className="text-xl font-bold text-slate-900">Daily Briefing</h1>
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            to="/"
            className={clsx(
              "text-sm font-medium no-underline",
              location.pathname === "/"
                ? "text-blue-600"
                : "text-slate-500 hover:text-slate-900"
            )}
          >
            Dashboard
          </Link>
          <Link
            to="/settings"
            className={clsx(
              "flex items-center gap-1 text-sm font-medium no-underline",
              location.pathname === "/settings"
                ? "text-blue-600"
                : "text-slate-500 hover:text-slate-900"
            )}
          >
            <Settings className="h-4 w-4" />
            Settings
          </Link>
        </nav>
      </div>
    </header>
  );
}
