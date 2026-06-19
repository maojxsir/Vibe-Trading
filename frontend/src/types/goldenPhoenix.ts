/** Wire types for GET /market/golden-phoenix and related endpoints. */

export interface GoldenPhoenixSignals {
  shrink_volume: boolean;
  volume_breakout: boolean;
  ma_bullish: boolean;
}

export interface GoldenPhoenixItem {
  code: string;
  name: string;
  board: string;
  status: "confirmed" | "watch" | string;
  score: number;
  t0_date: string;
  t1_date?: string | null;
  lifeline: number;
  callback_days: number;
  gap_days: number;
  price?: number | null;
  change_pct?: number | null;
  one_word_first_board: boolean;
  signals: GoldenPhoenixSignals;
  trade_date: string;
  industry?: string;
  main_business?: string;
  market_cap?: number | null;
  pe_ttm?: number | null;
  quarter_growth?: number | null;
}

export interface GoldenPhoenixPayload {
  strategy: string;
  tradeDate: string;
  items: GoldenPhoenixItem[];
  params: Record<string, unknown>;
  source: string;
  degraded: boolean;
  updatedAt: string;
  skipped: number;
  filtered_count: number;
  universe_count: number;
  matched_count: number;
  stale: boolean;
  stale_reason?: string;
}

export type GoldenPhoenixScanState = "idle" | "running" | "failed" | "done";

export interface GoldenPhoenixStatus {
  state: GoldenPhoenixScanState;
  progress: number;
  message: string;
  updatedAt: string;
}

export interface GoldenPhoenixRefreshResponse {
  accepted: boolean;
  message?: string;
}

export function formatGoldenPhoenixStatus(status: string): string {
  if (status === "confirmed") return "二板确认";
  if (status === "watch") return "蓄势待板";
  return status;
}

export function formatGoldenPhoenixSignals(signals: GoldenPhoenixSignals): string {
  const parts: string[] = [];
  if (signals.shrink_volume) parts.push("缩量");
  if (signals.volume_breakout) parts.push("放量");
  if (signals.ma_bullish) parts.push("MA多头");
  return parts.length ? parts.join(" · ") : "—";
}

export function formatScanTotals(payload: GoldenPhoenixPayload): string {
  const matched = payload.matched_count ?? payload.items.length;
  const universe =
    payload.universe_count ?? matched + payload.filtered_count + payload.skipped;
  return `扫描 ${universe.toLocaleString("zh-CN")} 只，命中 ${matched.toLocaleString("zh-CN")} 只`;
}

export function formatMarketCap(yuan?: number | null): string {
  if (yuan == null || !Number.isFinite(yuan) || yuan <= 0) return "—";
  const yi = yuan / 1e8;
  if (yi >= 10000) return `${(yi / 10000).toFixed(2)}万亿`;
  if (yi >= 100) return `${yi.toFixed(0)}亿`;
  return `${yi.toFixed(1)}亿`;
}
