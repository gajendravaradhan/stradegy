import { useState } from "react";

export default function Settings() {
  const [autonomy, setAutonomy] = useState<"semi" | "full">("semi");
  const [tradeMode, setTradeMode] = useState<"paper" | "live">("paper");

  return (
    <div className="p-4 safe-top">
      <h1 className="text-lg font-semibold mb-4">Settings</h1>

      <div className="space-y-5">
        <SettingSection title="Trading Mode">
          <RadioGroup
            options={[
              { value: "paper", label: "Paper Trading" },
              { value: "live", label: "Live (Alpaca)" },
            ]}
            value={tradeMode}
            onChange={(v) => setTradeMode(v as "paper" | "live")}
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
            value={autonomy}
            onChange={(v) => setAutonomy(v as "semi" | "full")}
          />
        </SettingSection>

        <SettingSection title="API Configuration">
          {["Alpaca Key", "Alpaca Secret", "Telegram Token", "Finnhub Key", "Reddit Client"].map(
            (label) => (
              <input
                key={label}
                type="password"
                placeholder={label}
                className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring mb-2"
              />
            ),
          )}
        </SettingSection>

        <SettingSection title="Risk Parameters">
          {[
            { label: "Max Drawdown", value: "20%" },
            { label: "Risk Per Trade", value: "3%" },
            { label: "Max Positions", value: "1" },
            { label: "Stop ATR Multiplier", value: "1.5x" },
          ].map((param) => (
            <div
              key={param.label}
              className="flex items-center justify-between py-2 border-b border-border last:border-0"
            >
              <span className="text-sm text-muted-foreground">{param.label}</span>
              <span className="text-sm font-mono-value">{param.value}</span>
            </div>
          ))}
        </SettingSection>

        <SettingSection title="Tax Settings">
          <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
            <span className="text-sm text-muted-foreground">Short-Term Rate</span>
            <span className="text-sm font-mono-value">30%</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-muted-foreground">Long-Term Rate</span>
            <span className="text-sm font-mono-value">15%</span>
          </div>
        </SettingSection>

        <div className="text-center py-2">
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
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
        {title}
      </p>
      <div className="bg-card border border-border rounded-lg p-3">
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
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`w-full text-left p-2 rounded-md transition-colors ${
            value === opt.value
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground"
          }`}
        >
          <div className="flex items-center gap-2">
            <div
              className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                value === opt.value
                  ? "border-accent-foreground"
                  : "border-muted-foreground"
              }`}
            >
              {value === opt.value && (
                <div className="w-2 h-2 rounded-full bg-accent-foreground" />
              )}
            </div>
            <span className="text-sm font-medium">{opt.label}</span>
          </div>
          {opt.description && (
            <p className="text-xs mt-1 ml-6 text-muted-foreground">
              {opt.description}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
