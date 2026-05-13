import { useNavigate } from "react-router-dom";
import { LucideIcon, LayoutDashboard, Sparkles, BriefcaseBusiness, TrendingUp, Settings } from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  LayoutDashboard,
  Sparkles,
  BriefcaseBusiness,
  TrendingUp,
  Settings,
};

interface TabBarProps {
  tabs: { path: string; label: string; icon: string }[];
  currentPath: string;
}

export default function TabBar({ tabs, currentPath }: TabBarProps) {
  const navigate = useNavigate();

  return (
    <nav className="flex items-center justify-around h-14 border-t border-border bg-card safe-bottom shrink-0">
      {tabs.map((tab) => {
        const active = currentPath === tab.path;
        const Icon = ICON_MAP[tab.icon];
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={`flex flex-col items-center justify-center gap-0.5 min-w-0 flex-1 h-full transition-colors ${
              active ? "text-accent-foreground" : "text-muted-foreground"
            }`}
          >
            {Icon && <Icon size={20} strokeWidth={active ? 2.5 : 1.5} />}
            <span className="text-[10px] font-medium">{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
