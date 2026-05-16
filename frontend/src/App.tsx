import { Routes, Route, useLocation } from "react-router-dom";
import { LayoutDashboard, Sparkles, BriefcaseBusiness, TrendingUp, Settings as SettingsIcon } from "lucide-react";
import TabBar from "./components/TabBar";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Portfolio from "./pages/Portfolio";
import Strategies from "./pages/Strategies";
import Settings from "./pages/Settings";

const TABS = [
  { path: "/", label: "Home", icon: LayoutDashboard },
  { path: "/alerts", label: "Gems", icon: Sparkles },
  { path: "/portfolio", label: "Portfolio", icon: BriefcaseBusiness },
  { path: "/strategies", label: "Strategies", icon: TrendingUp },
  { path: "/settings", label: "Settings", icon: SettingsIcon },
];

export default function App() {
  const location = useLocation();

  return (
    <div className="flex flex-col h-dvh max-w-lg mx-auto bg-background relative overflow-hidden">
      <main className="flex-1 overflow-y-auto overflow-x-hidden">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
      <TabBar tabs={TABS} currentPath={location.pathname} />
    </div>
  );
}
