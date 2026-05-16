const API_BASE = "/api";

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const msg = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${msg}`);
  }
  return res.json();
}

export function getAlerts(minScore = 50, limit = 20) {
  return fetchApi<AlertResponse[]>(`/alerts?min_score=${minScore}&limit=${limit}`);
}

export function getPortfolio() {
  return fetchApi<PortfolioResponse>("/portfolio");
}

export function getStrategies() {
  return fetchApi<StrategiesResponse>("/strategies");
}

export function getSettings() {
  return fetchApi<SettingsResponse>("/settings");
}

export function updateSettings(payload: Partial<SettingsResponse>) {
  return fetchApi<{ success: boolean; changed: string[] }>("/settings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getBacktestStrategies() {
  return fetchApi<{ strategies: BacktestStrategy[] }>("/backtest/strategies");
}

export function runBacktest(ticker: string, strategy: string, trainSize = 252, testSize = 63, stepSize = 63) {
  return fetchApi<BacktestResult>(`/backtest/run?ticker=${ticker}&strategy=${strategy}&train_size=${trainSize}&test_size=${testSize}&step_size=${stepSize}`, { method: "POST" });
}

export function getSparkline(symbol: string, days = 90) {
  return fetchApi<Array<{ date: string; close: number }>>(`/data/tickers/${symbol}/sparkline?days=${days}`);
}

interface AlertResponse {
  ticker: string;
  score: number;
  classification: string;
  source_count: number;
  reddit: number;
  discord: number;
  sec: number;
  news: number;
  technical: number;
  created_at: string;
}

interface PortfolioResponse {
  equity: number;
  buying_power: number;
  tax_reserve: number;
  day_pnl: number;
  open_positions: number;
  positions: Position[];
  mode: string;
  autonomy: string;
}

interface Position {
  symbol: string;
  qty: number;
  avg_entry_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
}

interface StrategiesResponse {
  strategies: Strategy[];
  ensemble_active: boolean;
  min_confidence: number;
  min_agreement: number;
}

interface Strategy {
  name: string;
  active: boolean;
  weight: number;
  description: string;
}

interface SettingsResponse {
  paper_trading: boolean;
  autonomy_mode: string;
  max_drawdown: number;
  risk_per_trade: number;
  max_positions: number;
  stop_atr_mult: number;
  tax_rate_short_term: number;
  tax_rate_long_term: number;
}

interface BacktestStrategy {
  key: string;
  name: string;
  description: string;
}

interface BacktestResult {
  ticker: string;
  strategy: string;
  windows_tested: number;
  aggregate: Record<string, number>;
  window_results: Array<{
    train_start: string;
    train_end: string;
    test_start: string;
    test_end: string;
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    total_trades: number;
  }>;
}
