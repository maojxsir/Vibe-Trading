// Curated seed for the 事件概率 (event probability) page.

export type EventDir = "利好" | "利空" | "中性";

export interface MarketEvent {
  event: string;
  probability: number; // 0-100
  affected: string;
  direction: EventDir;
  odds: string; // 赔率/弹性
}

export const eventsSeed: MarketEvent[] = [
  { event: "美联储下半年降息", probability: 65, affected: "成长股 / 黄金", direction: "利好", odds: "中" },
  { event: "1.6T 光模块明确放量", probability: 70, affected: "中际旭创 / 天孚通信", direction: "利好", odds: "高" },
  { event: "人形机器人量产落地超预期", probability: 45, affected: "减速器 / 丝杠 / 电机", direction: "利好", odds: "高" },
  { event: "海外 AI 资本开支下修", probability: 25, affected: "光模块 / PCB", direction: "利空", odds: "高" },
  { event: "长鑫存储 IPO 落地", probability: 55, affected: "国产存储链", direction: "利好", odds: "中" },
];
