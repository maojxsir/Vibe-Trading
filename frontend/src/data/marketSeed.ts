import type { MarketOverview } from "./types";

// Seed values mirror screenshot 1. Used for initial render and as the
// offline fallback when /market/overview is unavailable.
export const marketSeed: MarketOverview = {
  indices: [
    { name: "上证指数", code: "sh000001", price: 4083.97, changePct: 0.22 },
    { name: "深证成指", code: "sz399001", price: 15704.71, changePct: 0.73 },
    { name: "创业指数", code: "sz399006", price: 4122.99, changePct: 1.65 },
    { name: "沪深300", code: "sh000300", price: 4938.81, changePct: 0.49 },
    { name: "道琼斯", code: "usDJI", price: 51307.79, changePct: 0.45 },
    { name: "纳斯达克", code: "usIXIC", price: 27093.9, changePct: 0.03 },
    { name: "标普500", code: "usINX", price: 7609.78, changePct: 0.13 },
  ],
  humanoid: {
    note: "持仓: 绿的谐波（制造环节唯一）",
    stocks: [
      { name: "绿的谐波", code: "sh688017", tag: "持仓·谐波减速器", price: 314.88, changePct: 2.9, pe: 422.1, marketCap: 577 },
      { name: "三花智控", code: "sz002050", tag: "热管理/执行", price: 45.08, changePct: -0.2, pe: 46.4, marketCap: 1661 },
      { name: "拓普集团", code: "sh601689", tag: "执行器/丝杠", price: 62.63, changePct: -0.52, pe: 39.4, marketCap: 1088 },
      { name: "双环传动", code: "sz002472", tag: "减速器", price: 40.24, changePct: 0.65, pe: 26.9, marketCap: 301 },
      { name: "汇川技术", code: "sz300124", tag: "电机/驱动", price: 75.86, changePct: 0.66, pe: null, marketCap: 1828 },
      { name: "兆威机电", code: "sz003021", tag: "灵巧手/微型驱", price: 96.61, changePct: -0.66, pe: 107.5, marketCap: 200 },
    ],
  },
  aiCompute: {
    note: "未持仓: 估值偏高, 等回调",
    stocks: [
      { name: "中际旭创", code: "sz300308", tag: "光模块龙头", price: 1275.0, changePct: 6.98, pe: 95.1, marketCap: 14148 },
      { name: "沪电股份", code: "sz002463", tag: "PCB", price: 129.8, changePct: -0.92, pe: 58.1, marketCap: 2496 },
      { name: "胜宏科技", code: "sz300476", tag: "PCB", price: 353.44, changePct: 1.25, pe: 74.2, marketCap: 3058 },
      { name: "天孚通信", code: "sz300394", tag: "光模块/CPO", price: 497.38, changePct: 8.84, pe: 178.4, marketCap: 3868 },
      { name: "寒武纪", code: "sh688256", tag: "AI芯片", price: 1378.1, changePct: 6.01, pe: 318.7, marketCap: 8659 },
      { name: "海光信息", code: "sh688041", tag: "AI芯片", price: 285.94, changePct: 0.86, pe: 243.8, marketCap: 6646 },
    ],
  },
  updatedAt: "2026-06-03 17:33:47",
  source: "腾讯财经",
  stale: true,
};
