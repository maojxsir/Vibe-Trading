// Curated 市场总览 watchlists. Codes align with 人形机器人·估值全景 / AI算力·核心标的;
// tag / PE / PE(TTM) / 市值 are research snapshots; price / changePct come from live quotes only.

import type { IndexQuote, MarketOverview, StockQuote } from "./types";

export const MARKET_INDICES: IndexQuote[] = [
  { name: "上证指数", code: "sh000001", price: NaN, changePct: NaN },
  { name: "深证成指", code: "sz399001", price: NaN, changePct: NaN },
  { name: "创业指数", code: "sz399006", price: NaN, changePct: NaN },
  { name: "沪深300", code: "sh000300", price: NaN, changePct: NaN },
  { name: "道琼斯", code: "usDJI", price: NaN, changePct: NaN },
  { name: "纳斯达克", code: "usIXIC", price: NaN, changePct: NaN },
  { name: "标普500", code: "usINX", price: NaN, changePct: NaN },
];

/** Same six codes as 人形机器人 → 估值全景. */
export const HUMANOID_CORE_WATCHLIST: StockQuote[] = [
  { name: "绿的谐波", code: "sh688017", tag: "持仓·谐波减速器", price: NaN, changePct: NaN, pe: 422.1, peTtm: 422.13, marketCap: 577 },
  { name: "双环传动", code: "sz002472", tag: "减速器", price: NaN, changePct: NaN, pe: 26.9, peTtm: 26.94, marketCap: 301 },
  { name: "拓普集团", code: "sh601689", tag: "执行器/丝杠", price: NaN, changePct: NaN, pe: 39.4, peTtm: 39.4, marketCap: 1088 },
  { name: "三花智控", code: "sz002050", tag: "热管理/执行", price: NaN, changePct: NaN, pe: 46.4, peTtm: 46.4, marketCap: 1661 },
  { name: "汇川技术", code: "sz300124", tag: "电机/驱动", price: NaN, changePct: NaN, pe: null, peTtm: 38.2, marketCap: 1828 },
  { name: "兆威机电", code: "sz003021", tag: "灵巧手/微型驱", price: NaN, changePct: NaN, pe: 107.5, peTtm: 107.5, marketCap: 200 },
];

/** Same four codes as AI算力 → 核心标的 (coreFour). */
export const AI_COMPUTE_CORE_WATCHLIST: StockQuote[] = [
  { name: "中际旭创", code: "sz300308", tag: "光模块龙头", price: NaN, changePct: NaN, pe: 95.1, peTtm: 95.1, marketCap: 14148 },
  { name: "沪电股份", code: "sz002463", tag: "PCB", price: NaN, changePct: NaN, pe: 58.1, peTtm: 58.1, marketCap: 2496 },
  { name: "胜宏科技", code: "sz300476", tag: "PCB", price: NaN, changePct: NaN, pe: 74.2, peTtm: 74.2, marketCap: 3058 },
  { name: "天孚通信", code: "sz300394", tag: "光模块/CPO", price: NaN, changePct: NaN, pe: 178.4, peTtm: 178.4, marketCap: 3868 },
];

export function emptyMarketOverview(): MarketOverview {
  return {
    indices: MARKET_INDICES.map((i) => ({ ...i })),
    humanoid: {
      note: "与人形机器人·估值全景一致 · 持仓: 绿的谐波（制造环节唯一）",
      stocks: HUMANOID_CORE_WATCHLIST.map((s) => ({ ...s })),
    },
    aiCompute: {
      note: "与 AI算力·核心标的一致 · 未持仓: 估值偏高, 等回调",
      stocks: AI_COMPUTE_CORE_WATCHLIST.map((s) => ({ ...s })),
    },
    updatedAt: "—",
    source: "腾讯财经",
    stale: true,
  };
}
