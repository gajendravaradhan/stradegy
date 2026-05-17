import { useQuery } from "@tanstack/react-query";
import { TrendingUp, TrendingDown, Wallet, Receipt, Layers } from "lucide-react";
import { useState } from "react";
import { getPortfolio, getTier } from "../lib/api";

export default function Portfolio() {
  const [tab, setTab] = useState<"positions" | "history">("positions");
  const { data, isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: () => getPortfolio(),
    refetchInterval: 30_000,
  });
  const { data: tierData } = useQuery({
    queryKey: ["tier", data?.equity],
    queryFn: () => getTier(data?.equity),
    enabled: !!data,
    staleTime: 300_000,
  });

  if (isLoading || !data) {
    return (
      <div className="p-6 pb-28 animate-fade-in-up">
        <h1 className="text-xl font-semibold mb-6">Portfolio</h1>
        <div className="h-8 w-32 bg-muted/40 rounded-xl animate-pulse mb-6" />
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 pb-28 animate-fade-in-up">
      <h1 className="text-xl font-semibold mb-6">Portfolio</h1>

      <div className="mb-6">
        <div className="flex items-center justify-between">
          <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Total Equity</p>
          {tierData && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-primary/10 text-[10px] font-semibold uppercase tracking-wider">
              <Layers size={12} />
              {tierData.current.tier}
            </div>
          )}
        </div>
        <p className="text-3xl font-semibold font-mono-value mt-1.5 tracking-tight">
          ${data.equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
        {tierData && (
          <p className="text-[11px] text-muted-foreground mt-1">
            {tierData.current.description} · Max {tierData.current.max_positions} positions · {tierData.current.risk_per_trade * 100}% risk/trade
          </p>
        )}
      </div>

      <div className="glass rounded-2xl p-1 mb-6">
        <div className="flex">
          <button
            className={`flex-1 py-2.5 text-xs font-semibold rounded-xl transition-all ${
              tab === "positions"
                ? "bg-primary/20 text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setTab("positions")}
          >
            Positions ({data.open_positions})
          </button>
          <button
            className={`flex-1 py-2.5 text-xs font-semibold rounded-xl transition-all ${
              tab === "history"
                ? "bg-primary/20 text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setTab("history")}
          >
            Trade History
          </button>
        </div>
      </div>

      {tab === "positions" ? (
        data.positions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <div className="w-16 h-16 rounded-2xl bg-secondary/40 flex items-center justify-center mb-4">
              <Wallet size={28} className="opacity-30" />
            </div>
            <p className="text-sm font-medium">No open positions</p>
            <p className="text-xs mt-2">Approved gems will appear here</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.positions.map((pos, i) => (
              <div
                key={pos.symbol}
                className="glass rounded-2xl p-4 animate-fade-in-up"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-secondary/60 flex items-center justify-center text-sm font-bold">
                      {pos.symbol.slice(0, 2)}
                    </div>
                    <div>
                      <p className="text-sm font-semibold">{pos.symbol}</p>
                      <p className="text-[10px] text-muted-foreground">{pos.qty} shares</p>
                    </div>
                  </div>
                  <div className={`flex items-center gap-1 text-sm font-mono-value font-semibold ${
                    pos.unrealized_pl >= 0 ? "text-emerald-400" : "text-rose-400"
                  }`}>
                    {pos.unrealized_pl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    {(pos.unrealized_plpc * 100).toFixed(2)}%
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <p className="text-[10px] text-muted-foreground">Avg Price</p>
                    <p className="font-mono-value font-medium mt-0.5">${pos.avg_entry_price.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground">Market Value</p>
                    <p className="font-mono-value font-medium mt-0.5">${pos.market_value.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground">Unrealized P&L</p>
                    <p className={`font-mono-value font-medium mt-0.5 ${pos.unrealized_pl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {pos.unrealized_pl >= 0 ? "+" : ""}${pos.unrealized_pl.toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <p className="text-sm font-medium">No trade history yet</p>
        </div>
      )}

      <div className="glass rounded-2xl p-5 mt-6">
        <div className="flex items-center gap-2 mb-4">
          <Receipt size={14} className="text-muted-foreground" />
          <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Tax Summary</p>
        </div>
        <div className="space-y-3">
          <TaxRow label="Realized Gains" value="$0.00" />
          <TaxRow label="Tax Reserve (30%)" value="$0.00" accent="amber" />
          <TaxRow label="Available" value="$0.00" />
        </div>
      </div>
    </div>
  );
}

function TaxRow({ label, value, accent }: { label: string; value: string; accent?: "amber" }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm font-mono-value font-medium ${accent === "amber" ? "text-amber-400" : ""}`}>{value}</span>
    </div>
  );
}
