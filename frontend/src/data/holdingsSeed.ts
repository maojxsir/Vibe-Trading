// Curated seed for the 持仓决策 (holdings / decision) page.

export type DecisionAction = "加仓" | "减仓" | "持有" | "清仓";

export interface Holding {
  name: string;
  code: string;
  cost: number;
  price: number;
  position: number; // % of portfolio
  action: DecisionAction;
  reason: string;
}

export const holdingsSeed: Holding[] = [
  {
    name: "绿的谐波",
    code: "688017",
    cost: 248.5,
    price: 314.88,
    position: 42,
    action: "持有",
    reason: "人形机器人减速器制造环节唯一稀缺标的，业绩高增但估值偏高，逢大跌再加。",
  },
  {
    name: "汇川技术",
    code: "300124",
    cost: 68.2,
    price: 75.86,
    position: 20,
    action: "加仓",
    reason: "电机/驱动平台型龙头，PEG 相对合理，回调即加。",
  },
  {
    name: "双环传动",
    code: "002472",
    cost: 43.1,
    price: 40.24,
    position: 12,
    action: "持有",
    reason: "减速器产能弹性标的，等待份额兑现，跌破成本但逻辑未变。",
  },
];
