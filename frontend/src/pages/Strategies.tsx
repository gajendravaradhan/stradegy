import { useQuery } from "@tanstack/react-query";
import { Zap, ToggleLeft, ToggleRight } from "lucide-react";
import { useState } from "react";
import { getStrategies } from "../lib/api";

export default function Strategies() {
  const { data, isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => getStrategies(),
    refetchInterval: 60_000,
  });

  const [weights, setWeights] = useState<Record<string, number>>({});
  const [activeMap, setActiveMap] = useState<Record<string, boolean>>({});

  if (isLoading || !data) {
    return (
      <div className="p-6 pb-28 animate-fade-in-up">
        <h1 className="text-xl font-semibold mb-6">Strategies</h1>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const strategies = data.strategies;

  const toggleStrategy = (name: string) => {
    setActiveMap((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <div className="p-6 pb-28 animate-fade-in-up">
      <h1 className="text-xl font-semibold mb-6">Strategies</h1>

      <div className="glass rounded-2xl p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold">Ensemble</span>
          <span
            className={`text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${
              data.ensemble_active
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                : "bg-muted text-muted-foreground border border-border"
            }`}
          >
            {data.ensemble_active ? "Active" : "Inactive"}
          </span>
        </div>
        <div className="flex gap-6 text-xs text-muted-foreground">
          <span>Min Confidence: <span className="font-mono-value text-foreground">{data.min_confidence}</span></span>
          <span>Min Agreement: <span className="font-mono-value text-foreground">{data.min_agreement}</span></span>
        </div>
      </div>

      <div className="space-y-4">
        {strategies.map((s, i) => {
          const w = weights[s.name] ?? s.weight;
          const isActive = activeMap[s.name] ?? s.active;
          return (
            <div
              key={s.name}
              className="glass rounded-2xl p-5 animate-fade-in-up"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold">{s.name}</span>
                <button
                  className={`transition-colors ${
                    isActive ? "text-emerald-400" : "text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => toggleStrategy(s.name)}
                  aria-label={isActive ? "Deactivate" : "Activate"}
                >
                  {isActive ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mb-4">{s.description}</p>
              
              <div className="flex items-center gap-4 mb-4 text-xs text-muted-foreground">
                <span>Weight: <span className="font-mono-value text-foreground">{(w * 100).toFixed(0)}%</span></span>
                <span>Sharpe: <span className="font-mono-value text-foreground">{"sharpe" in s && (s as any).sharpe > 0 ? ((s as any).sharpe as number).toFixed(1) : "—"}</span></span>
                <span>P&L: <span className="font-mono-value text-foreground">{"pnl" in s ? `$${((s as any).pnl as number).toFixed(2)}` : "$0.00"}</span></span>
              </div>

              <div className="relative h-1.5 bg-secondary/60 rounded-full overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-primary/50 transition-all duration-300"
                  style={{ width: `${w * 100}%` }}
                />
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={w * 100}
                onChange={(e) =>
                  setWeights({ ...weights, [s.name]: Number(e.target.value) / 100 })
                }
                className="w-full mt-3 accent-primary opacity-0 absolute inset-0 cursor-pointer"
                style={{ position: "relative", opacity: 1, marginTop: 8 }}
              />
            </div>
          );
        })}
      </div>

      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <div className="w-12 h-12 rounded-xl bg-secondary/40 flex items-center justify-center mb-3">
          <Zap size={20} className="opacity-30" />
        </div>
        <p className="text-xs">Self-improvement cycle runs weekends</p>
      </div>
    </div>
  );
}
