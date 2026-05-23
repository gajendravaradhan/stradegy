import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, EyeOff, BarChart3, RefreshCw, Newspaper, TrendingUp, TrendingDown, Activity, MessageSquare, FileText, Radio, Sparkles } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { getTickerDetail, getSparkline, getTickerResearch, toggleWatchTicker } from "../lib/api";
import InteractiveSparkline from "../components/InteractiveSparkline";

export default function TickerDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: ticker, isLoading: tickerLoading, error: tickerError, refetch } = useQuery({
    queryKey: ["ticker", symbol],
    queryFn: () => getTickerDetail(symbol!),
    enabled: !!symbol,
    retry: 1,
    retryDelay: 2000,
  });

  const { data: sparklineData, isLoading: sparkLoading } = useQuery({
    queryKey: ["sparkline", symbol, 90],
    queryFn: () => getSparkline(symbol!, 90),
    enabled: !!symbol,
    staleTime: 60_000,
  });

  const { data: research, isLoading: researchLoading } = useQuery({
    queryKey: ["ticker-research", symbol],
    queryFn: () => getTickerResearch(symbol!, 7),
    enabled: !!symbol,
    staleTime: 300_000,
  });

  const watchMutation = useMutation({
    mutationFn: () => toggleWatchTicker(symbol!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ticker", symbol] });
      queryClient.invalidateQueries({ queryKey: ["tickers"] });
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const hasSparkline = sparklineData && sparklineData.length > 0;
  const currentPrice = hasSparkline ? sparklineData[sparklineData.length - 1].close : null;
  const previousPrice = hasSparkline && sparklineData.length > 1 ? sparklineData[sparklineData.length - 2].close : null;
  const priceChange = currentPrice && previousPrice ? currentPrice - previousPrice : 0;
  const priceChangePct = currentPrice && previousPrice && previousPrice !== 0 ? (priceChange / previousPrice) * 100 : 0;

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
    const isTimeout = tickerError instanceof Error && (
      tickerError.message.includes("timeout") || tickerError.message.includes("abort")
    );
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
          <p className="text-sm font-medium">
            {isTimeout ? "Request timed out" : "Ticker not found"}
          </p>
          <p className="text-xs mt-2 max-w-[240px] text-center leading-relaxed">
            {isTimeout
              ? "The server took too long to respond. Try again or check your connection."
              : `We couldn't find data for ${symbol?.toUpperCase()}.`}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-4 flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-colors"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      </div>
    );
  }

  const gem = research?.latest_gem;

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
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold">{ticker.symbol}</h1>
          <p className="text-sm text-muted-foreground truncate">{ticker.name || "—"}</p>
          {ticker.sector && (
            <span className="inline-block mt-1 px-2 py-0.5 rounded-md bg-primary/10 text-[10px] font-semibold uppercase tracking-wider">
              {ticker.sector}
            </span>
          )}
        </div>
        <button
          onClick={() => watchMutation.mutate()}
          disabled={watchMutation.isPending}
          className="p-2.5 rounded-xl bg-secondary/40 border border-border/30 hover:bg-white/5 transition-colors disabled:opacity-50"
          title={ticker.is_watched ? "Remove from watchlist" : "Add to watchlist"}
        >
          {watchMutation.isPending ? (
            <Eye size={18} className="animate-pulse text-muted-foreground" />
          ) : ticker.is_watched ? (
            <Eye size={18} className="text-amber-400" />
          ) : (
            <EyeOff size={18} className="text-muted-foreground" />
          )}
        </button>
      </div>

      {currentPrice !== null && (
        <div className="glass rounded-2xl p-5 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Current Price</p>
              <p className="text-3xl font-semibold font-mono-value mt-1">${currentPrice.toFixed(2)}</p>
              <div className={`flex items-center gap-1 mt-1 text-sm font-medium ${priceChange >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {priceChange >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                <span className="font-mono-value">
                  {priceChange >= 0 ? "+" : ""}{priceChange.toFixed(2)} ({priceChangePct >= 0 ? "+" : ""}{priceChangePct.toFixed(2)}%)
                </span>
              </div>
            </div>
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${priceChange >= 0 ? "bg-emerald-500/10" : "bg-rose-500/10"}`}>
              <Activity size={20} className={priceChange >= 0 ? "text-emerald-400" : "text-rose-400"} />
            </div>
          </div>
        </div>
      )}

      <div className="glass rounded-2xl p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">90-Day Trend</p>
          <span className="text-xs font-mono-value text-muted-foreground">
            {hasSparkline ? `$${sparklineData[sparklineData.length - 1].close.toFixed(2)}` : "—"}
          </span>
        </div>
        {hasSparkline ? (
          <InteractiveSparkline data={sparklineData} height={120} />
        ) : (
          <div className="h-32 flex items-center justify-center text-muted-foreground text-xs">
            {sparkLoading ? "Loading chart data..." : "No chart data available"}
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-4 mb-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Status</p>
            <p className="text-sm font-semibold mt-1">{ticker.is_active ? "Active" : "Inactive"}</p>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <span className={`w-2 h-2 rounded-full ${ticker.is_active ? "bg-emerald-400" : "bg-muted-foreground/40"}`} />
            <span className="text-xs">{ticker.is_active ? "Monitored" : "Not monitored"}</span>
          </div>
        </div>
      </div>

      {gem && (
        <div className="glass rounded-2xl p-4 mb-3">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={14} className="text-muted-foreground" />
            <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Latest Gem Signal</p>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-semibold font-mono-value">{gem.score?.toFixed(0) || "—"}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{gem.classification?.replace("_", " ") || "No signal"}</p>
            </div>
            <div className="text-right">
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider border ${
                gem.status === "executed" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20" :
                gem.status === "approved" ? "bg-primary/15 text-primary border-primary/20" :
                gem.status === "rejected" ? "bg-rose-500/15 text-rose-400 border-rose-500/20" :
                "bg-amber-500/15 text-amber-400 border-amber-500/20"
              }`}>
                {gem.status || "pending"}
              </span>
              <p className="text-[10px] text-muted-foreground mt-1">{gem.source_count} sources</p>
            </div>
          </div>
        </div>
      )}

      {research && research.news && research.news.length > 0 && (
        <div className="glass rounded-2xl p-4 mb-3">
          <div className="flex items-center gap-2 mb-3">
            <Newspaper size={14} className="text-muted-foreground" />
            <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Recent News</p>
          </div>
          <div className="space-y-3">
            {research.news.map((n, i) => (
              <a key={i} href={n.url} target="_blank" rel="noopener noreferrer" className="block">
                <div className="py-2 border-b border-border/20 last:border-0">
                  <p className="text-xs font-medium line-clamp-2">{n.headline}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-muted-foreground">{n.source}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      n.sentiment === "positive" ? "bg-emerald-500/10 text-emerald-400" :
                      n.sentiment === "negative" ? "bg-rose-500/10 text-rose-400" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {n.sentiment}
                    </span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {research && research.reddit && research.reddit.length > 0 && (
        <div className="glass rounded-2xl p-4 mb-3">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare size={14} className="text-muted-foreground" />
            <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Reddit Mentions</p>
          </div>
          <div className="space-y-3">
            {research.reddit.map((r, i) => (
              <a key={i} href={r.url} target="_blank" rel="noopener noreferrer" className="block">
                <div className="py-2 border-b border-border/20 last:border-0">
                  <p className="text-xs font-medium line-clamp-2">{r.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-muted-foreground">r/{r.subreddit}</span>
                    <span className="text-[10px] text-muted-foreground">{r.score} upvotes</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      r.sentiment > 0 ? "bg-emerald-500/10 text-emerald-400" :
                      r.sentiment < 0 ? "bg-rose-500/10 text-rose-400" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {r.sentiment > 0 ? "positive" : r.sentiment < 0 ? "negative" : "neutral"}
                    </span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {research && research.discord && research.discord.length > 0 && (
        <div className="glass rounded-2xl p-4 mb-3">
          <div className="flex items-center gap-2 mb-3">
            <Radio size={14} className="text-muted-foreground" />
            <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">Discord Mentions</p>
          </div>
          <div className="space-y-3">
            {research.discord.map((d, i) => (
              <a key={i} href={d.url} target="_blank" rel="noopener noreferrer" className="block">
                <div className="py-2 border-b border-border/20 last:border-0">
                  <p className="text-xs font-medium line-clamp-2">{d.content}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-muted-foreground">#{d.channel}</span>
                    <span className="text-[10px] text-muted-foreground">{d.reactions} reactions</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      d.sentiment > 0 ? "bg-emerald-500/10 text-emerald-400" :
                      d.sentiment < 0 ? "bg-rose-500/10 text-rose-400" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {d.sentiment > 0 ? "positive" : d.sentiment < 0 ? "negative" : "neutral"}
                    </span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {research && research.sec && research.sec.length > 0 && (
        <div className="glass rounded-2xl p-4 mb-3">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={14} className="text-muted-foreground" />
            <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium">SEC Filings</p>
          </div>
          <div className="space-y-3">
            {research.sec.map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="block">
                <div className="py-2 border-b border-border/20 last:border-0">
                  <p className="text-xs font-medium">{s.filing_type}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-muted-foreground">{s.filing_date ? new Date(s.filing_date).toLocaleDateString() : "—"}</span>
                    {s.revenue_growth !== null && (
                      <span className="text-[10px] text-emerald-400">Rev: +{(s.revenue_growth * 100).toFixed(1)}%</span>
                    )}
                    {s.insider_net_buys !== null && s.insider_net_buys > 0 && (
                      <span className="text-[10px] text-amber-400">Insider buys: {s.insider_net_buys}</span>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {researchLoading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      )}
    </div>
  );
}
