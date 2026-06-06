// Curated seed for the Serenity 方法论 (methodology) page.

export interface MethodSection {
  title: string;
  items: string[];
}

export const serenitySeed: MethodSection[] = [
  {
    title: "投资原则",
    items: [
      "只投自己看得懂的产业链环节，能说清「为什么是它」。",
      "用产业逻辑选方向，用估值（PEG / 演化时间）控买点。",
      "稀缺性优先：制造环节唯一、不可替代性强的标的给溢价。",
    ],
  },
  {
    title: "买卖纪律",
    items: [
      "分批建仓，单一标的仓位上限明确，避免一次打满。",
      "逻辑未破不轻易止损；逻辑破坏（份额/路线被替代）果断离场。",
      "估值过高（PEG 远大于 1、演化时间过长）等回调再介入。",
    ],
  },
  {
    title: "复盘检查清单",
    items: [
      "持仓逻辑是否仍然成立？有没有新的替代风险？",
      "估值相对业绩增速是否仍合理（PEG）？",
      "仓位结构是否过度集中？是否需要再平衡？",
    ],
  },
];
