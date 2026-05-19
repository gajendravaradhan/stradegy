import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Eye, EyeOff, BarChart3 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { getTickerDetail, getSparkline } from "../lib/api";

function SparklineChart({ data }: { data: Array<{ date: string; close: number }> }) {
  if (!data || data.length < 2) return null;

  const prices = data.map((d) => d.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 300;
  const height = 120;

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
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-32" preserveAspectRatio="none">
      <defs>
        <linearGradient id="detailAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={strokeColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#detailAreaGrad)" />
      <polyline fill="none" stroke={strokeColor} strokeWidth="2" points={points.join(" ")} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={points[points.length - 1].split(",")[0]} cy={points[points.length - 1].split(",")[1]} r="4" fill={strokeColor} stroke="white" strokeWidth="2" />
    </svg>
  );
}

export default function TickerDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();

  const { data: ticker, isLoading: tickerLoading, error: tickerError } = useQuery({
    queryKey: ["ticker", symbol],
    queryFn: () => getTickerDetail(symbol!),
    enabled: !!symbol,
  });

  const { data: sparklineData } = useQuery({
    queryKey: ["sparkline", symbol, 90],
    queryFn: () => getSparkline(symbol!, 90),
    enabled: !!symbol,
    staleTime: 60_000,
  });

  if (tickerLoading) {
    return (
      <div className="p-6 pb-28 animate-fade-in-up">
        <div className="h-8 w-32 bg-muted/40 rounded-xl animate-pulse mb-6" />
        <div className="h-32 bg-muted/40 rounded-2xl animate-pulse mb-6" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (tickerError || !ticker) {
    return (
      <div className="p-6 pb-28 animate-fade-in-up">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <BarChart3 size={28} className="opacity-30 mb-3" />
          <p className="text-sm">Ticker not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 pb-28 animate-fade-in-up">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      <div className="flex items-center gap-4 mb-6">
        <div className="w-14 h-14 rounded-2xl bg-secondary/60 flex items-center justify-center text-xl font-bold">
          {ticker.symbol.slice(0, 2)}
        </div>
        <div>
          <h1 className="text-2xl font-semibold">{ticker.symbol}</h1>
          <p className="text-sm text-muted-foreground">{ticker.name || "—"}</p>
          {ticker.sector && (
            <span className="inline-block mt-1 px-2 py-0.5 rounded-md bg-primary/10 text-[10px] font-semibold uppercase tracking-wider">
              {ticker.sector}
            </span>
          )}
        </div>
      </div>

      <div className="glass rounded-2xl p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">90-Day Trend</p>
          <span className="text-xs font-mono-value text-muted-foreground">
            {sparklineData && sparklineData.length > 0
              ? `$${sparklineData[sparklineData.length - 1].close.toFixed(2)}`
              : "—"}
          </span>
        </div>
        {sparklineData && sparklineData.length > 0 ? (
          <SparklineChart data={sparklineData} />
        ) : (
          <div className="h-32 flex items-center justify-center text-muted-foreground text-xs">
            No chart data available
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div className="glass rounded-2xl p-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Status</p>
            <p className="text-sm font-semibold mt-1">{ticker.is_active ? "Active" : "Inactive"}</p>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            {ticker.is_watched ? <Eye size={16} className="text-amber-400" /> : <EyeOff size={16} />}
          </div>
        </div>

        <button
          className="w-full glass rounded-2xl p-4 flex items-center justify-center gap-2 text-sm font-semibold hover:bg-white/5 transition-colors"
          onClick={() => {}}
        >
          {ticker.is_watched ? (
            <>
              <EyeOff size={16} />
              Unwatch
            </>
          ) : (
            <>
              <Eye size={16} />
              Watch
            </>
          )}
        </button>
      </div>
    </div>
  );
}
