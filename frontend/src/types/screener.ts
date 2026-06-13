/** Wire types for GET /market/screener and related endpoints. */

export interface ScreenerSignals {
  limitup: number;
  volume: number;
  gap: number;
  yang: number;
}

export interface ScreenerVetoes {
  low_position?: boolean;
  distribution?: boolean;
  /** Already overextended: short/long cumulative gain too large. */
  overextended?: boolean;
}

export interface ScreenerItem {
  code: string;
  name: string;
  board: string;
  score: number;
  signals: ScreenerSignals;
  vetoes: ScreenerVetoes;
  position_pct: number;
  untradable: boolean;
  trade_date: string;
  /** 行业板块（Tushare stock_basic.industry），可能缺失。 */
  industry?: string;
  /** 主营业务（Tushare stock_company.main_business），可能缺失。 */
  main_business?: string;
  /** 总市值（元，Tushare daily_basic.total_mv*1e4），可能缺失。 */
  market_cap?: number | null;
  /** 现价（Tushare daily_basic.close），可能缺失。 */
  price?: number | null;
  /** 市盈率 TTM（Tushare daily_basic.pe_ttm），可能缺失/为负。 */
  pe_ttm?: number | null;
  /** 最近季度增速：单季净利润同比（%, fina_indicator.q_profit_yoy），可能缺失。 */
  quarter_growth?: number | null;
  /** 连续入选天数（1=新增）。 */
  membership_days?: number;
  /** 连续入选状态：新增 / N天 / 删除。 */
  membership_status?: string;
}

export interface ScreenerPayload {
  tradeDate: string;
  items: ScreenerItem[];
  params: Record<string, unknown>;
  source: string;
  degraded: boolean;
  updatedAt: string;
  skipped: number;
  filtered_count: number;
  /** Total symbols in the scan universe (after ST / listing filters). */
  universe_count: number;
  /** Symbols that passed required signals and entered the result set. */
  matched_count: number;
  stale: boolean;
  /** Present when ``stale`` is true (e.g. policy_updated). */
  stale_reason?: string;
}

export type ScreenerScanState = "idle" | "running" | "failed" | "done";

export interface ScreenerStatus {
  state: ScreenerScanState;
  progress: number;
  message: string;
  updatedAt: string;
}

export interface ScreenerRefreshResponse {
  accepted: boolean;
  message?: string;
}

export const SIGNAL_KEYS = ["limitup", "volume", "gap", "yang"] as const;
export type ScreenerSignalKey = (typeof SIGNAL_KEYS)[number];

/** Must be present for a stock to enter the screener result set. */
export const REQUIRED_SIGNAL_KEYS = ["limitup", "volume"] as const;
export type ScreenerRequiredSignalKey = (typeof REQUIRED_SIGNAL_KEYS)[number];

/** Optional bonus signals that improve ranking but are not required. */
export const OPTIONAL_SIGNAL_KEYS = ["gap", "yang"] as const;

export const SIGNAL_LABELS: Record<ScreenerSignalKey, string> = {
  limitup: "涨停",
  volume: "量能",
  gap: "跳空",
  yang: "连阳",
};

/** Compact four-signal summary for Agent prompts and opportunity triggers. */
export function formatSignalSummary(signals: ScreenerSignals): string {
  return SIGNAL_KEYS.map((k) => `${SIGNAL_LABELS[k]} ${Math.round(signals[k] * 100)}%`).join(" · ");
}

/** Human-readable scan totals for toasts and footer hints. */
export function formatScanTotals(payload: ScreenerPayload): string {
  const matched = payload.matched_count ?? payload.items.length;
  const universe =
    payload.universe_count ?? matched + payload.filtered_count + payload.skipped;
  return `扫描 ${universe.toLocaleString("zh-CN")} 只，命中 ${matched.toLocaleString("zh-CN")} 只`;
}

export function hasActiveVeto(vetoes: ScreenerVetoes): boolean {
  return Object.values(vetoes).some(Boolean);
}

/** 把总市值（元）格式化为「亿」展示，缺失返回「—」。 */
export function formatMarketCap(yuan?: number | null): string {
  if (yuan == null || !Number.isFinite(yuan) || yuan <= 0) return "—";
  const yi = yuan / 1e8;
  if (yi >= 10000) return `${(yi / 10000).toFixed(2)}万亿`;
  if (yi >= 100) return `${yi.toFixed(0)}亿`;
  return `${yi.toFixed(1)}亿`;
}
