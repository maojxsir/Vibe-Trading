// Curated research content for the 人形机器人 (humanoid robot) page.
// Mirrors screenshot 3; values are hand-curated research data.

import { collectModuleCodes, type ModuleStock } from "./types";

export type { ModuleStock };

export interface ValuationRow {
  name: string;
  code: string;
  module: string;
  price: number;
  peTtm: number | null;
  pb: number;
  cap: number; // 总市值(亿)
  q1Growth: number; // Q1增速 %
  peg: string;
  digest: string; // 演化时间
  stars: number; // 0-5
  irreplace: string; // 不可替代性 tag
  rating: string; // 评级
}

export interface ChainSection {
  heading: string;
  points: string[];
}

export interface HumanoidData {
  meta: { based: string; dataDate: string; marketTime: string };
  tabs: string[];
  overviewIntro: string;
  valuationSubtitle: string;
  valuation: ValuationRow[];
  sections: Record<string, ChainSection>;
  moduleStocks: Record<string, ModuleStock[]>;
}

export function allHumanoidModuleCodes(data: HumanoidData): string[] {
  return collectModuleCodes(
    data.moduleStocks,
    data.valuation.map((r) => r.code),
  );
}

export const humanoidSeed: HumanoidData = {
  meta: {
    based: "基于 170 篇 2026 研报·覆盖 19 家核心标的",
    dataDate: "数据日期: 2026-05-25",
    marketTime: "市场数据: 17:34:21 更新",
  },
  tabs: [
    "总览", "成本构成", "减速器", "丝杠", "电机", "传感器", "腱绳/新材料", "替代风险", "估值全景", "宇树科技",
  ],
  overviewIntro:
    "人形机器人产业链以执行器（减速器/丝杠/电机）为价值核心，传感器与灵巧手随构型升级占比提升。当前主线在谐波减速器国产替代、行星滚柱丝杠突破，以及整机量产带来的供应链卡位。",
  valuationSubtitle: "19 家核心标的的实时估值 | 数据更新: 2026-05-23 (最近交易日)",
  valuation: [
    { name: "绿的谐波", code: "688017", module: "减速器", price: 314.88, peTtm: 422.13, pb: 16.18, cap: 577.27, q1Growth: 61.2, peg: "4.90", digest: "4.8年", stars: 4, irreplace: "tech", rating: "买入" },
    { name: "双环传动", code: "002472", module: "减速器", price: 40.24, peTtm: 26.94, pb: 3.32, cap: 301.21, q1Growth: 2.9, peg: "8.03", digest: "已<30x", stars: 3, irreplace: "capacity", rating: "优于大市" },
    { name: "拓普集团", code: "601689", module: "执行器/丝杠", price: 62.63, peTtm: 39.4, pb: 5.1, cap: 1088.0, q1Growth: 18.5, peg: "2.13", digest: "2.1年", stars: 4, irreplace: "tech", rating: "买入" },
    { name: "三花智控", code: "002050", module: "热管理/执行", price: 45.08, peTtm: 46.4, pb: 6.4, cap: 1661.0, q1Growth: 22.1, peg: "2.10", digest: "2.0年", stars: 4, irreplace: "tech", rating: "买入" },
    { name: "汇川技术", code: "300124", module: "电机/驱动", price: 75.86, peTtm: 38.2, pb: 7.2, cap: 1828.0, q1Growth: 25.4, peg: "1.50", digest: "1.5年", stars: 5, irreplace: "platform", rating: "买入" },
    { name: "兆威机电", code: "003021", module: "灵巧手/微型驱", price: 96.61, peTtm: 107.5, pb: 11.3, cap: 200.0, q1Growth: 35.0, peg: "3.07", digest: "3.1年", stars: 3, irreplace: "tech", rating: "增持" },
  ],
  sections: {
    成本构成: {
      heading: "成本构成",
      points: [
        "执行器（含减速器/丝杠/电机）占整机成本约 50%，是价值量核心",
        "灵巧手与传感器随构型升级，价值占比有望提升",
        "规模化后减速器/丝杠降本空间最大",
      ],
    },
    减速器: {
      heading: "减速器",
      points: [
        "谐波减速器为旋转关节核心，绿的谐波国产龙头、制造环节稀缺",
        "双环传动以产能与成本见长，份额提升逻辑清晰",
      ],
    },
    丝杠: {
      heading: "丝杠",
      points: [
        "行星滚柱丝杠用于直线关节，精度与寿命要求高、国产突破中",
        "拓普集团等切入，工艺与设备是壁垒",
      ],
    },
    电机: {
      heading: "电机",
      points: [
        "无框力矩电机 + 空心杯电机为关节驱动核心",
        "汇川技术平台能力强，电机/驱动一体化受益",
      ],
    },
    传感器: {
      heading: "传感器",
      points: [
        "六维力/力矩传感器、触觉传感器为感知关键",
        "国产化率低、弹性大，关注良率与标定能力",
      ],
    },
    "腱绳/新材料": {
      heading: "腱绳 / 新材料",
      points: [
        "腱绳传动用于灵巧手，PEEK 等高性能材料需求提升",
        "轻量化与耐磨是材料选型核心",
      ],
    },
    替代风险: {
      heading: "替代风险",
      points: [
        "构型路线（直驱 vs 腱绳、丝杠 vs 减速器）变化带来环节替代风险",
        "海外供应链导入节奏影响国产份额兑现",
      ],
    },
    宇树科技: {
      heading: "宇树科技 (Unitree)",
      points: [
        "整机标杆，量产节奏与降本路径是行业风向标",
        "供应链卡位带动上游核心零部件需求",
      ],
    },
  },
  moduleStocks: {
    成本构成: [
      { name: "拓普集团", code: "601689", industry: "执行器总成", module: "执行器", heatBase: 84, logic: "丝杠+执行器一体化，价值量最高环节" },
      { name: "绿的谐波", code: "688017", industry: "谐波减速器", module: "减速器", heatBase: 86, logic: "旋转关节核心，成本占比约 20%" },
      { name: "汇川技术", code: "300124", industry: "伺服驱动", module: "电机", heatBase: 82, logic: "驱控平台能力，关节电机受益" },
      { name: "三花智控", code: "002050", industry: "热管理", module: "热管理", heatBase: 78, logic: "关节散热与液冷配套" },
    ],
    减速器: [
      { name: "绿的谐波", code: "688017", industry: "谐波减速器", module: "减速器", heatBase: 88, logic: "国产谐波龙头，制造稀缺" },
      { name: "双环传动", code: "002472", industry: "RV/谐波", module: "减速器", heatBase: 76, logic: "产能与成本优势，份额提升" },
      { name: "中大力德", code: "002896", industry: "行星减速器", module: "减速器", heatBase: 68, logic: "微型行星减速，灵巧手配套" },
    ],
    丝杠: [
      { name: "拓普集团", code: "601689", industry: "行星滚柱丝杠", module: "丝杠", heatBase: 83, logic: "直线关节核心，工艺壁垒高" },
      { name: "恒立液压", code: "601100", industry: "精密丝杠", module: "丝杠", heatBase: 74, logic: "丝杠设备与加工能力" },
      { name: "贝斯特", code: "300580", industry: "滚珠丝杠", module: "丝杠", heatBase: 70, logic: "丝杠副国产突破" },
    ],
    电机: [
      { name: "汇川技术", code: "300124", industry: "无框力矩/伺服", module: "电机", heatBase: 85, logic: "电机+驱动一体化平台" },
      { name: "兆威机电", code: "003021", industry: "微型驱动", module: "电机", heatBase: 77, logic: "灵巧手/空心杯电机" },
      { name: "鸣志电器", code: "603728", industry: "空心杯电机", module: "电机", heatBase: 73, logic: "高扭矩密度驱动" },
    ],
    传感器: [
      { name: "柯力传感", code: "603662", industry: "力矩传感", module: "传感器", heatBase: 72, logic: "六维力/力矩，国产化率低" },
      { name: "汉威科技", code: "300007", industry: "柔性传感", module: "传感器", heatBase: 66, logic: "触觉/柔性传感布局" },
      { name: "睿能科技", code: "603933", industry: "力控传感", module: "传感器", heatBase: 64, logic: "关节力控标定" },
    ],
    "腱绳/新材料": [
      { name: "中研股份", code: "688716", industry: "PEEK", module: "新材料", heatBase: 71, logic: "腱绳/轻量化高性能材料" },
      { name: "金发科技", code: "600143", industry: "改性塑料", module: "新材料", heatBase: 58, logic: "耐磨轻量化材料配套" },
    ],
    替代风险: [
      { name: "秦川机床", code: "000837", industry: "精密传动", module: "替代路线", heatBase: 55, logic: "丝杠/减速器路线替代观察" },
      { name: "步科股份", code: "688160", industry: "直驱电机", module: "替代路线", heatBase: 52, logic: "直驱 vs 减速器构型风险" },
    ],
    估值全景: [
      { name: "绿的谐波", code: "688017", industry: "谐波减速器", module: "减速器", heatBase: 88, logic: "稀缺制造+高增速" },
      { name: "拓普集团", code: "601689", industry: "执行器/丝杠", module: "丝杠", heatBase: 84, logic: "特斯拉/宇树供应链" },
      { name: "汇川技术", code: "300124", industry: "电机/驱动", module: "电机", heatBase: 85, logic: "平台型龙头" },
      { name: "三花智控", code: "002050", industry: "热管理/执行", module: "执行器", heatBase: 80, logic: "热管理+执行器双受益" },
      { name: "双环传动", code: "002472", industry: "RV/谐波", module: "减速器", heatBase: 76, logic: "估值消化中" },
      { name: "兆威机电", code: "003021", industry: "灵巧手/微型驱", module: "电机", heatBase: 74, logic: "灵巧手弹性" },
    ],
    宇树科技: [
      { name: "拓普集团", code: "601689", industry: "执行器", module: "供应链", heatBase: 86, logic: "整机执行器核心供应商" },
      { name: "三花智控", code: "002050", industry: "热管理", module: "供应链", heatBase: 80, logic: "关节热管理配套" },
      { name: "绿的谐波", code: "688017", industry: "谐波减速器", module: "供应链", heatBase: 84, logic: "旋转关节减速器卡位" },
      { name: "汇川技术", code: "300124", industry: "驱控", module: "供应链", heatBase: 78, logic: "驱控平台潜在受益" },
    ],
  },
};
