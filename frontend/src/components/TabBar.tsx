import { useNavigate } from "react-router-dom";
import { LucideIcon } from "lucide-react";

interface Tab {
  path: string;
  label: string;
  icon: LucideIcon;
}

interface TabBarProps {
  tabs: Tab[];
  currentPath: string;
}

export default function TabBar({ tabs, currentPath }: TabBarProps) {
  const navigate = useNavigate();

  return (
    <div className="absolute bottom-0 left-0 right-0 z-50 pb-[calc(env(safe-area-inset-bottom,0px)+8px)] px-6">
      <nav className="glass-strong rounded-2xl h-14 flex items-center justify-around">
        {tabs.map((tab) => {
          const active = currentPath === tab.path;
          const Icon = tab.icon;
          return (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              className="relative flex flex-col items-center justify-center min-w-[56px] h-full transition-all duration-300 ease-out"
            >
              <div
                className={`flex items-center justify-center w-9 h-9 rounded-xl transition-all duration-300 ${
                  active
                    ? "bg-primary/20 text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon size={20} strokeWidth={active ? 2.5 : 1.5} />
              </div>
              {active && (
                <span className="absolute -bottom-0.5 w-1 h-1 rounded-full bg-primary" />
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
