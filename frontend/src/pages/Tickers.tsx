import { useQuery } from "@tanstack/react-query";
import { Search, BarChart3, Eye, EyeOff, ChevronRight } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getTickers, getSparkline } from "../lib/api";

function MiniSparkline({ symbol }: { symbol: string }) {
  const { data } = useQuery({
    queryKey: ["sparkline", symbol, 30],
    queryFn: () => getSparkline(symbol, 30),
    staleTime: 60_000,
  });

  if (!data || data.length < 2) {
    return <div className="w-20 h-8 bg-muted/30 rounded-md" />;
  }

  const prices = data.map((d) => d.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 80;
  const height = 32;

  const points = prices.map((price, i) => {
    const x = (i / (prices.length - 1)) * width;
    const y = height - ((price - min) / range) * (height - 6) - 3;
    return `${x},${y}`;
  });

  const isProfit = prices[prices.length - 1] >= prices[0];
  const color = isProfit ? "hsl(142 76% 45%)" : "hsl(0 72% 51%)";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-20 h-8" preserveAspectRatio="none">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points.join(" ")} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Tickers() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const { data: tickers, isLoading } = useQuery({
    queryKey: ["tickers"],
    queryFn: () => getTickers(true),
    refetchInterval: 300_000,
  });

  const filtered = tickers?.filter((t) => {
    const q = query.toUpperCase();
    return t.symbol.toUpperCase().includes(q) || (t.name || "").toUpperCase().includes(q);
  });

  const sectors = [...new Set((tickers || []).map((t) => t.sector).filter(Boolean))];

  return (
    <div className="p-6 pb-28 animate-fade-in-up">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Tickers</h1>
        <span className="text-xs text-muted-foreground font-mono-value">
          {tickers?.length || 0} active
        </span>
      </div>

      <div className="relative mb-6">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search symbol or name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full h-11 pl-10 pr-4 rounded-xl bg-secondary/40 border border-border/30 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {sectors.length > 0 && !query && (
        <div className="flex gap-2 overflow-x-auto pb-4 mb-2 scrollbar-hide">
          <button className="px-3 py-1.5 rounded-lg bg-primary/15 text-primary-foreground text-[11px] font-semibold whitespace-nowrap">
            All
          </button>
          {sectors.map((s) => (
            <button
              key={s}
              className="px-3 py-1.5 rounded-lg bg-secondary/40 text-muted-foreground text-[11px] font-medium whitespace-nowrap hover:text-foreground transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered && filtered.length > 0 ? (
        <div className="space-y-2.5">
          {filtered.map((ticker) => (
            <button
              key={ticker.symbol}
              onClick={() => navigate(`/tickers/${ticker.symbol}`)}
              className="w-full glass rounded-2xl p-4 flex items-center justify-between hover:bg-white/5 transition-colors text-left"
            >
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-secondary/60 flex items-center justify-center text-sm font-bold">
                  {ticker.symbol.slice(0, 2)}
                </div>
                <div>
                  <p className="text-sm font-semibold">{ticker.symbol}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {ticker.name || "—"} · {ticker.sector || "Unknown"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <MiniSparkline symbol={ticker.symbol} />
                <div className="flex items-center gap-1 text-muted-foreground">
                  {ticker.is_watched ? <Eye size={14} className="text-amber-400" /> : <EyeOff size={14} />}
                  <ChevronRight size={14} />
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <BarChart3 size={28} className="opacity-30 mb-3" />
          <p className="text-sm">No tickers found</p>
        </div>
      )}
    </div>
  );
}
