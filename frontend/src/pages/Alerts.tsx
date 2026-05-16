import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { getAlerts } from "../lib/api";

function ScoreRing({ score, size = 48 }: { score: number; size?: number }) {
  const circumference = 2 * Math.PI * ((size - 4) / 2);
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "hsl(142 76% 45%)" : score >= 65 ? "hsl(38 92% 50%)" : "hsl(220 10% 55%)";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={(size - 4) / 2} fill="none" stroke="hsl(225 15% 18%)" strokeWidth="3" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size - 4) / 2}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1s ease-out" }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-mono-value font-bold">
        {score}
      </span>
    </div>
  );
}

export default function Alerts() {
  const { data, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => getAlerts(),
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="p-6 pb-28 animate-fade-in-up">
        <h1 className="text-xl font-semibold mb-6">Hidden Gems</h1>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const alerts = data || [];

  return (
    <div className="p-6 pb-28 animate-fade-in-up">
      <h1 className="text-xl font-semibold mb-6">Hidden Gems</h1>

      {alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <div className="w-16 h-16 rounded-2xl bg-secondary/40 flex items-center justify-center mb-4">
            <Sparkles size={28} className="opacity-40" />
          </div>
          <p className="text-sm font-medium">No gems discovered yet</p>
          <p className="text-xs mt-2 max-w-[200px] text-center leading-relaxed">
            The research pipeline scans Reddit, Discord, SEC filings, and news to find opportunities
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert, i) => (
            <div
              key={`${alert.ticker}-${alert.created_at}`}
              className="glass rounded-2xl p-5 animate-fade-in-up"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-secondary/60 flex items-center justify-center text-sm font-bold">
                    {alert.ticker.slice(0, 2)}
                  </div>
                  <div>
                    <span className="text-base font-semibold">{alert.ticker}</span>
                    <span
                      className={`ml-2 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        alert.score >= 80
                          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                          : alert.score >= 65
                          ? "bg-amber-500/15 text-amber-400 border border-amber-500/20"
                          : "bg-muted text-muted-foreground border border-border"
                      }`}
                    >
                      {alert.classification.replace("_", " ")}
                    </span>
                  </div>
                </div>
                <ScoreRing score={Math.round(alert.score)} />
              </div>

              <div className="grid grid-cols-5 gap-2">
                <SourcePill label="Reddit" value={alert.reddit} max={25} />
                <SourcePill label="Discord" value={alert.discord ?? 0} max={25} />
                <SourcePill label="SEC" value={alert.sec} max={30} />
                <SourcePill label="News" value={alert.news} max={20} />
                <SourcePill label="Tech" value={alert.technical} max={25} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SourcePill({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.min((value / max) * 100, 100);
  const isStrong = pct >= 70;

  return (
    <div className="text-center">
      <div className="relative h-1.5 bg-secondary/60 rounded-full mb-2 overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ${
            isStrong ? "bg-emerald-400/70" : "bg-primary/40"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="text-xs font-mono-value font-semibold mt-0.5">{value.toFixed(1)}</p>
    </div>
  );
}
