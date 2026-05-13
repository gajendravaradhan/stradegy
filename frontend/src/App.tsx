import { Routes, Route, useLocation } from "react-router-dom";
import TabBar from "./components/TabBar";
import Dashboard from "./pages/Dashboard";
import Alerts from "./pages/Alerts";
import Portfolio from "./pages/Portfolio";
import Strategies from "./pages/Strategies";
import Settings from "./pages/Settings";

const TABS = [
  { path: "/", label: "Home", icon: "LayoutDashboard" as const },
  { path: "/alerts", label: "Alerts", icon: "Sparkles" as const },
  { path: "/portfolio", label: "Portfolio", icon: "BriefcaseBusiness" as const },
  { path: "/strategies", label: "Strategies", icon: "TrendingUp" as const },
  { path: "/settings", label: "Settings", icon: "Settings" as const },
];

export default function App() {
  const location = useLocation();

  return (
    <div className="flex flex-col h-dvh max-w-lg mx-auto bg-background">
      <main className="flex-1 overflow-y-auto">
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
