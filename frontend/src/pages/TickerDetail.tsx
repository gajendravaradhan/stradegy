import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, EyeOff, BarChart3, Info } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { getTickerDetail, getSparkline, toggleWatchTicker } from "../lib/api";
import InteractiveSparkline from "../components/InteractiveSparkline";

export default function TickerDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

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

  const watchMutation = useMutation({
    mutationFn: () => toggleWatchTicker(symbol!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticker", symbol] });
      queryClient.invalidateQueries({ queryKey: ["tickers"] });
    },
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
          <InteractiveSparkline data={sparklineData} height={120} />
        ) : (
          <div className="h-32 flex items-center justify-center text-muted-foreground text-xs">
            No chart data available
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div className="glass rounded-2xl p-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-1.5">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Status</p>
              <div className="group relative">
                <Info size={12} className="text-muted-foreground/60 cursor-help" />
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 px-3 py-2 rounded-lg bg-popover text-popover-foreground text-[11px] shadow-lg border border-border/40 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                  {ticker.is_active
                    ? "This ticker is in the active trading universe and is monitored for signals."
                    : "This ticker is not currently monitored for trading signals."}
                </div>
              </div>
            </div>
            <p className="text-sm font-semibold mt-1">{ticker.is_active ? "Active" : "Inactive"}</p>
          </div>
          <div className="flex items-center gap-1 text-muted-foreground">
            {ticker.is_watched ? <Eye size={16} className="text-amber-400" /> : <EyeOff size={16} />}
          </div>
        </div>

        <button
          className="w-full glass rounded-2xl p-4 flex items-center justify-center gap-2 text-sm font-semibold hover:bg-white/5 transition-colors disabled:opacity-50"
          onClick={() => watchMutation.mutate()}
          disabled={watchMutation.isPending}
        >
          {watchMutation.isPending ? (
            <Eye size={16} className="animate-pulse" />
          ) : ticker.is_watched ? (
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
