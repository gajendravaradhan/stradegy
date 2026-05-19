import { useQuery } from "@tanstack/react-query";
import { getSettings, updateSettings, getSecrets, updateSecrets } from "../lib/api";
import { useAppStore } from "../store/appStore";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

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

        <VaultSecretsSection />

        <div className="text-center py-4">
          <p className="text-xs text-muted-foreground">Stradegy v2.0.0</p>
        </div>
      </div>
    </div>
  );
}

function VaultSecretsSection() {
  const queryClient = useQueryClient();
  const { data: secrets, isLoading } = useQuery({
    queryKey: ["secrets"],
    queryFn: () => getSecrets(),
    staleTime: 300_000,
  });

  const updateMutation = useMutation({
    mutationFn: updateSecrets,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["secrets"] });
    },
  });

  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [visible, setVisible] = useState<Record<string, boolean>>({});

  if (isLoading) {
    return (
      <SettingSection title="Vault Secrets">
        <div className="h-32 bg-muted/40 rounded-2xl animate-pulse" />
      </SettingSection>
    );
  }

  const s = secrets || {
    alpaca_api_key: "",
    alpaca_secret_key: "",
    finnhub_api_key: "",
    discord_bot_token: "",
    discord_user_id: "",
    discord_general_channel_id: "",
  };

  const fields = [
    { key: "alpaca_api_key", label: "Alpaca API Key", masked: true },
    { key: "alpaca_secret_key", label: "Alpaca Secret Key", masked: true },
    { key: "finnhub_api_key", label: "Finnhub API Key", masked: true },
    { key: "discord_bot_token", label: "Discord Bot Token", masked: true },
    { key: "discord_user_id", label: "Discord User ID", masked: false },
    { key: "discord_general_channel_id", label: "Discord Channel ID", masked: false },
  ];

  const hasChanges = Object.values(inputs).some((v) => v.length > 0);

  return (
    <SettingSection title="Vault Secrets">
      <div className="space-y-3">
        {fields.map((f) => {
          const currentValue = s[f.key as keyof typeof s] || "";
          const inputValue = inputs[f.key] ?? "";
          const isVisible = visible[f.key] || false;
          const isMasked = f.masked && !isVisible && !inputValue;
          const displayValue = inputValue || (isMasked ? currentValue : currentValue);

          return (
            <div key={f.key} className="space-y-1.5">
              <label className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
                {f.label}
              </label>
              <div className="relative">
                <input
                  type={f.masked && !isVisible ? "password" : "text"}
                  value={displayValue}
                  placeholder={currentValue ? "••••••••" : "Not set"}
                  onChange={(e) => setInputs((prev) => ({ ...prev, [f.key]: e.target.value }))}
                  className="w-full bg-secondary/40 border border-border/50 rounded-xl px-3 py-2.5 text-sm font-mono-value focus:outline-none focus:border-primary/50 transition-colors"
                />
                {f.masked && (
                  <button
                    type="button"
                    onClick={() => setVisible((prev) => ({ ...prev, [f.key]: !prev[f.key] }))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {isVisible ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                )}
              </div>
            </div>
          );
        })}

        <button
          onClick={() => {
            const payload: Record<string, string> = {};
            Object.entries(inputs).forEach(([key, val]) => {
              if (val.trim().length > 0) payload[key] = val.trim();
            });
            if (Object.keys(payload).length > 0) {
              updateMutation.mutate(payload, {
                onSuccess: () => setInputs({}),
              });
            }
          }}
          disabled={!hasChanges || updateMutation.isPending}
          className="w-full py-2.5 rounded-xl bg-primary/15 text-primary border border-primary/20 text-sm font-semibold hover:bg-primary/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed mt-2"
        >
          {updateMutation.isPending ? "Saving..." : "Save Secrets"}
        </button>
        {updateMutation.isSuccess && (
          <p className="text-xs text-emerald-400 text-center">Secrets updated. Restart container to apply.</p>
        )}
      </div>
    </SettingSection>
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
