import { useQuery } from "@tanstack/react-query";
import { getSettings, updateSettings } from "../lib/api";
import { useAppStore } from "../store/appStore";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export default function Settings() {
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => getSettings(),
  });

  const queryClient = useQueryClient();
  const autonomyMode = useAppStore((s) => s.autonomyMode);
  const tradeMode = useAppStore((s) => s.tradeMode);
  const setAutonomyMode = useAppStore((s) => s.setAutonomyMode);
  const setTradeMode = useAppStore((s) => s.setTradeMode);

  const updateMutation = useMutation({
    mutationFn: updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const handleTradeModeChange = (value: "paper" | "live") => {
    setTradeMode(value);
    updateMutation.mutate({ paper_trading: value === "paper" });
  };

  const handleAutonomyChange = (value: "semi" | "full") => {
    setAutonomyMode(value);
    updateMutation.mutate({ autonomy_mode: value });
  };

  if (isLoading || !data) {
    return (
      <div className="p-6 pb-28 animate-fade-in-up">
        <h1 className="text-xl font-semibold mb-6">Settings</h1>
        <div className="space-y-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-muted/40 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 pb-28 animate-fade-in-up">
      <h1 className="text-xl font-semibold mb-6">Settings</h1>

      <div className="space-y-6">
        <SettingSection title="Trading Mode">
          <RadioGroup
            options={[
              { value: "paper", label: "Paper Trading", description: "Practice with simulated money" },
              { value: "live", label: "Live Trading", description: "Trade with real capital via Alpaca" },
            ]}
            value={tradeMode}
            onChange={handleTradeModeChange}
          />
        </SettingSection>

        <SettingSection title="Autonomy Mode">
          <RadioGroup
            options={[
              {
                value: "semi",
                label: "Semi-Autonomous",
                description: "Bot suggests trades, you approve or reject",
              },
              {
                value: "full",
                label: "Full-Autonomous",
                description: "Bot trades without asking",
              },
            ]}
            value={autonomyMode}
            onChange={handleAutonomyChange}
          />
        </SettingSection>

        <SettingSection title="Risk Parameters">
          {[
            { label: "Max Drawdown", value: `${(data.max_drawdown * 100).toFixed(0)}%` },
            { label: "Risk Per Trade", value: `${(data.risk_per_trade * 100).toFixed(0)}%` },
            { label: "Max Positions", value: String(data.max_positions) },
            { label: "Stop ATR Multiplier", value: `${data.stop_atr_mult}x` },
          ].map((param) => (
            <div
              key={param.label}
              className="flex items-center justify-between py-3 border-b border-border/30 last:border-0"
            >
              <span className="text-sm text-muted-foreground">{param.label}</span>
              <span className="text-sm font-mono-value font-semibold">{param.value}</span>
            </div>
          ))}
        </SettingSection>

        <SettingSection title="Tax Settings">
          <div className="flex items-center justify-between py-3 border-b border-border/30 last:border-0">
            <span className="text-sm text-muted-foreground">Short-Term Rate</span>
            <span className="text-sm font-mono-value font-semibold">{(data.tax_rate_short_term * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center justify-between py-3">
            <span className="text-sm text-muted-foreground">Long-Term Rate</span>
            <span className="text-sm font-mono-value font-semibold">{(data.tax_rate_long_term * 100).toFixed(0)}%</span>
          </div>
        </SettingSection>

        <div className="text-center py-4">
          <p className="text-xs text-muted-foreground">Stradegy v0.1.0</p>
        </div>
      </div>
    </div>
  );
}

function SettingSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-[11px] text-muted-foreground tracking-[0.15em] uppercase font-medium mb-3">
        {title}
      </p>
      <div className="glass rounded-2xl p-4">
        {children}
      </div>
    </div>
  );
}

function RadioGroup({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string; description?: string }[];
  value: string;
  onChange: (value: any) => void;
}) {
  return (
    <div className="space-y-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`w-full text-left p-3 rounded-xl transition-all ${
            value === opt.value
              ? "bg-primary/15 text-primary-foreground border border-primary/20"
              : "text-muted-foreground hover:bg-white/5"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                value === opt.value
                  ? "border-primary"
                  : "border-muted-foreground/40"
              }`}
            >
              {value === opt.value && (
                <div className="w-2.5 h-2.5 rounded-full bg-primary" />
              )}
            </div>
            <div>
              <span className="text-sm font-semibold">{opt.label}</span>
              {opt.description && (
                <p className="text-xs mt-0.5 text-muted-foreground">
                  {opt.description}
                </p>
              )}
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
