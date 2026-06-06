// Curated seed for the 事件概率 (event probability) page.
//
// Probability is a human judgement (no public feed), so it is editable and
// persisted. Each event may list affected tickers whose live quotes are shown
// as a supporting signal on the page.

export type EventDir = "利好" | "利空" | "中性";

export interface AffectedTicker {
  name: string;
  code: string;
}

export interface MarketEvent {
  event: string;
  probability: number; // 0-100, human-maintained
  affected: string; // free-text affected scope
  tickers: AffectedTicker[]; // tickers with live quotes (may be empty for macro)
  direction: EventDir;
  odds: string; // 赔率/弹性
}

export const eventsSeed: MarketEvent[] = [
  { event: "美联储下半年降息", probability: 65, affected: "成长股 / 黄金", tickers: [], direction: "利好", odds: "中" },
  {
    event: "1.6T 光模块明确放量",
    probability: 70,
    affected: "中际旭创 / 天孚通信",
    tickers: [
      { name: "中际旭创", code: "300308" },
      { name: "天孚通信", code: "300394" },
    ],
    direction: "利好",
    odds: "高",
  },
  {
    event: "人形机器人量产落地超预期",
    probability: 45,
    affected: "减速器 / 丝杠 / 电机",
    tickers: [
      { name: "绿的谐波", code: "688017" },
      { name: "双环传动", code: "002472" },
      { name: "拓普集团", code: "601689" },
    ],
    direction: "利好",
    odds: "高",
  },
  {
    event: "海外 AI 资本开支下修",
    probability: 25,
    affected: "光模块 / PCB",
    tickers: [
      { name: "中际旭创", code: "300308" },
      { name: "沪电股份", code: "002463" },
    ],
    direction: "利空",
    odds: "高",
  },
  { event: "长鑫存储 IPO 落地", probability: 55, affected: "国产存储链", tickers: [], direction: "利好", odds: "中" },
];
