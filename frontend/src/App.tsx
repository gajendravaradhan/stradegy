import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { LayoutDashboard, Sparkles, BriefcaseBusiness, Settings as SettingsIcon, BarChart3, Bookmark } from "lucide-react";
import TabBar from "./components/TabBar";
import ErrorBoundary from "./components/ErrorBoundary";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Portfolio from "./pages/Portfolio";
import Strategies from "./pages/Strategies";
import Tickers from "./pages/Tickers";
import TickerDetail from "./pages/TickerDetail";
import Watchlist from "./pages/Watchlist";
import Settings from "./pages/Settings";
import { useWebSocket } from "./hooks/useWebSocket";
import { usePullToRefresh } from "./hooks/usePullToRefresh";
import { useSwipeNavigation } from "./hooks/useSwipeNavigation";
import { useAppBadge } from "./hooks/useAppBadge";

const TABS = [
  { path: "/", label: "Home", icon: LayoutDashboard },
  { path: "/tickers", label: "Tickers", icon: BarChart3 },
  { path: "/watchlist", label: "Watchlist", icon: Bookmark },
  { path: "/alerts", label: "Gems", icon: Sparkles },
  { path: "/portfolio", label: "Portfolio", icon: BriefcaseBusiness },
  { path: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function App() {
  const location = useLocation();
  useWebSocket();
  usePullToRefresh();
  useSwipeNavigation(TABS);
  useAppBadge();

  return (
    <div className="flex flex-col max-w-lg mx-auto bg-background relative overflow-hidden app-height">
      <main className="flex-1 overflow-y-auto overflow-x-hidden">
        <ErrorBoundary>
          <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tickers" element={<Tickers />} />
          <Route path="/tickers/:symbol" element={<TickerDetail />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </ErrorBoundary>
      </main>
      <TabBar tabs={TABS} currentPath={location.pathname} />
    </div>
  );
}
