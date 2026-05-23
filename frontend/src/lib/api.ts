const API_BASE = "/api";
const API_TIMEOUT = 10000;

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const msg = await res.text().catch(() => "Unknown error");
      throw new Error(`API ${res.status}: ${msg}`);
    }
    return res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

export function getAlerts(minScore = 50, limit = 20) {
  return fetchApi<AlertResponse[]>(`/alerts?min_score=${minScore}&limit=${limit}`);
}

export function approveAlert(gemId: number) {
  return fetchApi<{ success: boolean; gem_id: number; status: string; order?: Record<string, unknown> | null }>(`/alerts/${gemId}/approve`, { method: "POST" });
}

export function rejectAlert(gemId: number) {
  return fetchApi<{ success: boolean; gem_id: number; status: string }>(`/alerts/${gemId}/reject`, { method: "POST" });
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

export function getSecrets() {
  return fetchApi<{
    alpaca_api_key: string;
    alpaca_secret_key: string;
    finnhub_api_key: string;
    discord_bot_token: string;
    discord_user_id: string;
    discord_general_channel_id: string;
  }>("/secrets");
}

export function updateSecrets(payload: Record<string, string>) {
  return fetchApi<{ success: boolean; updated: string[] }>("/secrets", {
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

export function getTickers(activeOnly = true) {
  return fetchApi<Array<{ symbol: string; name: string | null; sector: string | null; is_active: boolean; is_watched: boolean }>>(
    `/data/tickers?active_only=${activeOnly}`
  );
}

export function getWatchlist() {
  return fetchApi<Array<{ symbol: string; name: string | null; sector: string | null; is_active: boolean; is_watched: boolean }>>(
    `/data/tickers?active_only=true&watched_only=true`
  );
}

export function getTickerDetail(symbol: string) {
  return fetchApi<{ symbol: string; name: string | null; sector: string | null; is_active: boolean; is_watched: boolean }>(
    `/data/tickers/${symbol}`
  );
}

export function toggleWatchTicker(symbol: string) {
  return fetchApi<{ symbol: string; is_watched: boolean }>(`/data/tickers/${symbol}/watch`, { method: "POST" });
}

export function getTier(equity?: number) {
  const query = equity !== undefined ? `?equity=${equity}` : "";
  return fetchApi<{
    current: { tier: string; max_positions: number; risk_per_trade: number; description: string };
    all_tiers: Array<{ name: string; min_equity: number; max_equity: number | null; max_positions: number; risk_per_trade: number; description: string }>;
  }>(`/tier${query}`);
}

export function getSparkline(symbol: string, days = 90) {
  return fetchApi<Array<{ date: string; close: number }>>(`/data/tickers/${symbol}/sparkline?days=${days}`);
}

export function getPortfolioHistory(days = 90) {
  return fetchApi<{ days: number; count: number; history: Array<{ date: string; equity: number; buying_power: number; day_pnl: number; open_positions: number; drawdown: number }> }>(`/portfolio/history?days=${days}`);
}

export function getPerformanceMetrics(days = 90) {
  return fetchApi<{
    total_trades: number;
    win_rate: number;
    sharpe_ratio: number;
    max_drawdown: number;
    profit_factor: number;
    avg_win: number;
    avg_loss: number;
    total_pnl: number;
    expectancy: number;
    period_days: number;
  }>(`/portfolio/metrics?days=${days}`);
}

export function getTickerResearch(symbol: string, days = 7) {
  return fetchApi<{
    symbol: string;
    news: Array<{ headline: string; url: string; source: string; sentiment: string; confidence: number; published_at: string | null }>;
    reddit: Array<{ title: string; url: string; subreddit: string; score: number; sentiment: number }>;
    discord: Array<{ content: string; url: string; channel: string; reactions: number; sentiment: number }>;
    sec: Array<{ filing_type: string; filing_date: string | null; url: string; revenue_growth: number | null; insider_net_buys: number | null }>;
    latest_gem: { score: number | null; classification: string | null; source_count: number | null; status: string | null; created_at: string | null } | null;
  }>(`/data/tickers/${symbol}/research?days=${days}`);
}

export function getActivity(limit = 20) {
  return fetchApi<{
    activity: Array<{
      type: string;
      timestamp: string | null;
      ticker: string;
      action: string;
      details: string;
      status: string;
      pnl: number | null;
    }>;
  }>(`/activity?limit=${limit}`);
}

export function getTrades(ticker?: string, limit = 50, days = 90) {
  let url = `/trades?limit=${limit}&days=${days}`;
  if (ticker) url += `&ticker=${ticker}`;
  return fetchApi<{
    count: number;
    trades: Array<{
      id: number;
      ticker: string;
      action: string;
      price: number;
      shares: number;
      strategy: string | null;
      status: string;
      pnl: number | null;
      mode: string;
      created_at: string | null;
      notes: string | null;
    }>;
  }>(url);
}

export interface AlertResponse {
  id: number;
  ticker: string;
  score: number;
  classification: string;
  source_count: number;
  reddit: number;
  discord: number;
  sec: number;
  news: number;
  technical: number;
  status: string;
  created_at: string;
}

interface PortfolioResponse {
  equity: number;
  buying_power: number;
  tax_reserve: number;
  day_pnl: number;
  open_positions: number;
  positions: Position[];
  realized_gains: number;
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

export function getHealth() {
  return fetchApi<{
    version: string;
    mode: string;
    autonomy: string;
    alpaca_connected: boolean;
    finnhub_connected: boolean;
    discord_connected: boolean;
    data: {
      tickers: number;
      ohlcv_rows: number;
      gems: number;
      trades: number;
      active_tickers: number;
      latest_gem_at: string | null;
    };
  }>("/health/detailed");
}

export function triggerScan(type: "incremental" | "full" = "incremental") {
  return fetchApi<{ success: boolean; message: string }>(`/research/scan?type=${type}`, { method: "POST" });
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
