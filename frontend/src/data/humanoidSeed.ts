// Curated research content for the 人形机器人 (humanoid robot) page.
// Mirrors screenshot 3; values are hand-curated research data.

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
  valuationSubtitle: string;
  valuation: ValuationRow[];
  sections: Record<string, ChainSection>;
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
};
