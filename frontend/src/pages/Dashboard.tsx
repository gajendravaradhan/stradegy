import { useQuery } from "@tanstack/react-query";
import { TrendingUp, TrendingDown, Activity, Wallet, ChevronDown } from "lucide-react";
import { useState } from "react";
import { getPortfolio, getSparkline, getTickers } from "../lib/api";

function SparklineChart({ data }: { data: Array<{ date: string; close: number }> }) {
  if (!data || data.length < 2) return null;

  const prices = data.map((d) => d.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 300;
  const height = 100;

  const points = prices.map((price, i) => {
    const x = (i / (prices.length - 1)) * width;
    const y = height - ((price - min) / range) * (height - 20) - 10;
    return `${x},${y}`;
  });

  const isProfit = prices[prices.length - 1] >= prices[0];
  const strokeColor = isProfit ? "hsl(142 76% 45%)" : "hsl(0 72% 51%)";

  const areaPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p}`)
    .join(" ")
    .concat(` L ${width},${height} L 0,${height} Z`);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-24" preserveAspectRatio="none">
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#areaGrad)" />
      <polyline fill="none" stroke={strokeColor} strokeWidth="2" points={points.join(" ")} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={points[points.length - 1].split(",")[0]} cy={points[points.length - 1].split(",")[1]} r="4" fill={strokeColor} stroke="white" strokeWidth="2" />
    </svg>
  );
}

export default function Dashboard() {
  const [selectedTicker, setSelectedTicker] = useState("AAPL");
  const [showPicker, setShowPicker] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["account"],
    queryFn: () => getPortfolio(),
    refetchInterval: 30_000,
  });

  const { data: tickers } = useQuery({
    queryKey: ["tickers"],
    queryFn: () => getTickers(true),
    staleTime: 300_000,
  });

  const { data: sparklineData } = useQuery({
    queryKey: ["sparkline", selectedTicker],
    queryFn: () => getSparkline(selectedTicker, 90),
    refetchInterval: 60_000,
  });

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-6 animate-fade-in-up">
        <div className="h-10 w-40 bg-muted/40 rounded-xl animate-pulse" />
        <div className="h-16 w-56 bg-muted/40 rounded-xl animate-pulse" />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const isProfit = data.day_pnl >= 0;
  const pnlPct = data.equity > 0 ? (data.day_pnl / data.equity) * 100 : 0;

  return (
    <div className="p-6 pb-28 space-y-6 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Portfolio Value</p>
          <h1 className="text-4xl font-semibold font-mono-value mt-1.5 tracking-tight">
            ${data.equity.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </h1>
          <div className={`flex items-center gap-1.5 mt-2.5 text-sm font-medium ${isProfit ? "text-emerald-400" : "text-rose-400"}`}>
            {isProfit ? <TrendingUp size={15} /> : <TrendingDown size={15} />}
            <span className="font-mono-value">
              {isProfit ? "+" : ""}${data.day_pnl.toFixed(2)} ({pnlPct.toFixed(2)}%)
            </span>
          </div>
        </div>
        <span className={`px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
          data.mode === "paper"
            ? "bg-amber-500/15 text-amber-400 border border-amber-500/20"
            : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
        }`}>
          {data.mode === "paper" ? "Paper" : "Live"}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <GlassStat label="Buying Power" value={`$${data.buying_power.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
        <GlassStat label="Tax Reserve" value={`$${data.tax_reserve.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} accent="amber" />
        <GlassStat label="Positions" value={String(data.open_positions)} accent={data.open_positions > 0 ? "blue" : undefined} />
      </div>

      <div className="glass rounded-2xl p-5 relative">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setShowPicker(!showPicker)}
            className="flex items-center gap-1 text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium hover:text-foreground transition-colors"
          >
            {selectedTicker} Trend
            <ChevronDown size={12} />
          </button>
          <span className="text-xs font-mono-value text-muted-foreground">
            {sparklineData ? `$${sparklineData[sparklineData.length - 1]?.close.toFixed(2)}` : "—"}
          </span>
        </div>
        {showPicker && tickers && (
          <div className="absolute top-12 left-4 right-4 max-h-48 overflow-y-auto glass rounded-xl border border-border/40 z-10 p-2 space-y-1">
            {tickers.map((t) => (
              <button
                key={t.symbol}
                onClick={() => { setSelectedTicker(t.symbol); setShowPicker(false); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm ${t.symbol === selectedTicker ? "bg-primary/15 font-semibold" : "hover:bg-white/5"}`}
              >
                {t.symbol} <span className="text-muted-foreground text-xs">{t.name || ""}</span>
              </button>
            ))}
          </div>
        )}
        {sparklineData && sparklineData.length > 0 ? (
          <SparklineChart data={sparklineData} />
        ) : (
          <div className="h-24 flex items-center justify-center text-muted-foreground text-xs">
            No chart data
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-5">
        <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium mb-4">
          Open Positions ({data.open_positions})
        </p>
        {data.open_positions === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground gap-2">
            <Wallet size={28} className="opacity-30" />
            <p className="text-sm">No open positions</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.positions.map((pos, i) => (
              <div
                key={pos.symbol}
                className="flex items-center justify-between py-2.5 border-b border-border/30 last:border-0"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-secondary/60 flex items-center justify-center text-[11px] font-bold">
                    {pos.symbol.slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{pos.symbol}</p>
                    <p className="text-[10px] text-muted-foreground">{pos.qty} shares</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-mono-value font-medium ${pos.unrealized_pl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {pos.unrealized_pl >= 0 ? "+" : ""}${pos.unrealized_pl.toFixed(2)}
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono-value">
                    {(pos.unrealized_plpc * 100).toFixed(2)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={14} className="text-muted-foreground" />
          <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Recent Activity</p>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
          <p className="text-sm">No recent activity</p>
        </div>
      </div>
    </div>
  );
}

function GlassStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "blue" | "amber" | "green" | "red";
}) {
  const accentMap = {
    blue: "from-blue-500/10 to-transparent border-blue-500/20",
    amber: "from-amber-500/10 to-transparent border-amber-500/20",
    green: "from-emerald-500/10 to-transparent border-emerald-500/20",
    red: "from-rose-500/10 to-transparent border-rose-500/20",
  };
  const gradient = accent ? accentMap[accent] : "from-white/5 to-transparent border-white/10";

  return (
    <div className={`glass rounded-2xl p-4 bg-gradient-to-br ${gradient}`}>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-sm font-mono-value font-semibold mt-1.5">{value}</p>
    </div>
  );
}
