import { Sparkles } from "lucide-react";

export default function Alerts() {
  return (
    <div className="p-4 safe-top">
      <h1 className="text-lg font-semibold mb-4">Hidden Gems</h1>

      <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
        {["All", "Reddit", "SEC/News", "High Score"].map((f) => (
          <button
            key={f}
            className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap ${
              f === "All"
                ? "bg-accent text-accent-foreground"
                : "bg-card border border-border text-muted-foreground"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <Sparkles size={40} strokeWidth={1} className="mb-3 opacity-50" />
        <p className="text-sm font-medium">No gems discovered yet</p>
        <p className="text-xs mt-1">
          The research pipeline will scan Reddit, SEC filings, and news
        </p>
      </div>
    </div>
  );
}
