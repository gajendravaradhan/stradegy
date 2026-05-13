import { BriefcaseBusiness } from "lucide-react";
import { useState } from "react";

export default function Portfolio() {
  const [tab, setTab] = useState<"positions" | "history">("positions");

  return (
    <div className="p-4 safe-top">
      <h1 className="text-lg font-semibold mb-4">Portfolio</h1>

      <div className="flex bg-card rounded-lg p-0.5 border border-border mb-4">
        <button
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
            tab === "positions" ? "bg-accent text-accent-foreground" : "text-muted-foreground"
          }`}
          onClick={() => setTab("positions")}
        >
          Positions
        </button>
        <button
          className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
            tab === "history" ? "bg-accent text-accent-foreground" : "text-muted-foreground"
          }`}
          onClick={() => setTab("history")}
        >
          Trade History
        </button>
      </div>

      {tab === "positions" ? (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <BriefcaseBusiness size={40} strokeWidth={1} className="mb-3 opacity-50" />
          <p className="text-sm font-medium">No open positions</p>
          <p className="text-xs mt-1">Approved gems will appear here</p>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <p className="text-sm font-medium">No trade history yet</p>
        </div>
      )}

      <div className="bg-card border border-border rounded-lg p-4 mt-4">
        <p className="text-xs text-muted-foreground mb-3">Tax Summary</p>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Realized Gains</span>
            <span className="font-mono-value">$0.00</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Tax Reserve (30%)</span>
            <span className="font-mono-value text-amber-400">$0.00</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Available</span>
            <span className="font-mono-value">$0.00</span>
          </div>
        </div>
      </div>
    </div>
  );
}
