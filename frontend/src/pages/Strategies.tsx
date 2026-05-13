import { Zap } from "lucide-react";

export default function Strategies() {
  return (
    <div className="p-4 safe-top">
      <h1 className="text-lg font-semibold mb-4">Strategy Engine</h1>

      <div className="bg-card border border-border rounded-lg p-3 mb-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Capital Tier</span>
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-accent">
            Micro ($200 - $500)
          </span>
        </div>
        <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
          <span>Max: 1 position</span>
          <span>Risk: 3% / trade</span>
        </div>
      </div>

      <div className="space-y-3">
        {[
          { name: "Mean Reversion", active: true, weight: 100, sharpe: 0, pnl: 0 },
          { name: "Momentum Breakout", active: false, weight: 0, sharpe: 0, pnl: 0 },
          { name: "Earnings Momentum", active: false, weight: 0, sharpe: 0, pnl: 0 },
        ].map((s) => (
          <div
            key={s.name}
            className="bg-card border border-border rounded-lg p-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{s.name}</span>
              <span
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                  s.active
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {s.active ? "ON" : "OFF"}
              </span>
            </div>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              <span>Weight: {s.weight}%</span>
              <span>Sharpe: {s.sharpe > 0 ? s.sharpe.toFixed(1) : "—"}</span>
              <span>P&L: ${s.pnl.toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Zap size={32} strokeWidth={1} className="mb-2 opacity-50" />
        <p className="text-xs">Self-improvement cycle runs weekends</p>
      </div>
    </div>
  );
}
