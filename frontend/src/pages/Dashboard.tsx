import { useQuery } from "@tanstack/react-query";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["account"],
    queryFn: () => fetcher("/api/account/summary"),
    refetchInterval: 30_000,
  });

  if (isLoading || !data) {
    return (
      <div className="p-4 space-y-4">
        <div className="h-8 w-32 bg-muted rounded animate-pulse" />
        <div className="h-14 w-48 bg-muted rounded animate-pulse" />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-5 safe-top">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Stradegy</h1>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            data.mode === "paper"
              ? "bg-amber-500/20 text-amber-400"
              : "bg-emerald-500/20 text-emerald-400"
          }`}
        >
          {data.mode === "paper" ? "Paper" : "Live"}
        </span>
      </div>

      <div>
        <p className="text-xs text-muted-foreground mb-1">Total Equity</p>
        <p className="text-3xl font-semibold font-mono-value">
          ${data.equity.toFixed(2)}
        </p>
        <p
          className={`text-sm font-medium ${
            data.day_pnl >= 0 ? "text-profit" : "text-loss"
          }`}
        >
          {data.day_pnl >= 0 ? "+" : ""}${data.day_pnl.toFixed(2)} today
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Buying Power" value={`$${data.buying_power.toFixed(2)}`} />
        <StatCard label="Tax Reserve" value={`$${data.tax_reserve.toFixed(2)}`} />
        <StatCard label="Day P&L" value={`$${data.day_pnl.toFixed(2)}`} accent />
      </div>

      <div className="bg-card border border-border rounded-lg p-4">
        <p className="text-xs text-muted-foreground mb-3">Equity Curve</p>
        <div className="h-32 flex items-center justify-center text-muted-foreground text-sm">
          Chart will load with trading data
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-4">
        <p className="text-xs text-muted-foreground mb-3">Open Positions ({data.open_positions})</p>
        {data.open_positions === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No open positions
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">Positions loading...</p>
        )}
      </div>

      <div className="bg-card border border-border rounded-lg p-4">
        <p className="text-xs text-muted-foreground mb-3">Recent Activity</p>
        <p className="text-sm text-muted-foreground text-center py-4">
          No recent activity
        </p>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className={`bg-card border border-border rounded-lg p-3 ${accent ? value.startsWith("-$") ? "border-loss/30" : value.startsWith("-$") ? "" : "border-profit/30" : ""}`}>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
        {label}
      </p>
      <p className="text-sm font-mono-value font-medium mt-1">{value}</p>
    </div>
  );
}
