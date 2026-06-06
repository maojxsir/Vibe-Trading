// Curated research content for the AI算力 (AI compute) industry-chain page.
// Mirrors screenshot 2; values are hand-curated research data, not live-computed.

export interface CoreFourCol {
  name: string;
  price: number;
  changePct: number;
  cap: string; // 总市值
  peg: string;
  digest: string; // 消化时间
  logic: string; // 核心逻辑
}

export interface ChainSection {
  heading: string;
  points: string[];
}

export interface AIComputeData {
  meta: { updated: string; layers: string; count: string; score: string; sources: string };
  tabs: string[];
  overviewIntro: string;
  coreFour: CoreFourCol[];
  sections: Record<string, ChainSection>;
}

export const aiComputeSeed: AIComputeData = {
  meta: {
    updated: "2026-05-27 更新",
    layers: "5层14环节",
    count: "16只标的",
    score: "L1评分 83.8",
    sources: "数据来源: 1171条研报 + LightCounting + SemiAnalysis + Bernstein",
  },
  tabs: [
    "总览", "光模块", "PCB/HDI", "HBM/存储", "长鑫·IPO", "CPU/GPU",
    "下游企业", "算力能源", "太空算力", "核心标的", "估值全景", "AI新闻",
  ],
  overviewIntro:
    "AI 算力产业链覆盖光模块、PCB/HDI、HBM/存储、CPU/GPU、算力能源等 5 层 14 环节。当前主线集中在光模块（CPO 升级）与高端 PCB，海外资本开支维持高增，国产替代提速。",
  coreFour: [
    { name: "中际旭创", price: 1275.0, changePct: 6.98, cap: "14148亿", peg: "0.19", digest: "0.4年", logic: "全球龙头+PEG<1" },
    { name: "沪电股份", price: 129.8, changePct: -0.92, cap: "2496亿", peg: "0.96", digest: "1.4年", logic: "三线扩产+提速" },
    { name: "胜宏科技", price: 353.44, changePct: 1.25, cap: "3058亿", peg: "3.80", digest: "4.8年", logic: "AI概念+份额第一" },
    { name: "天孚通信", price: 497.38, changePct: 8.84, cap: "3868亿", peg: "3.80", digest: "4.7年", logic: "材料受益+CPO机会" },
  ],
  sections: {
    光模块: {
      heading: "光模块",
      points: [
        "800G 放量、1.6T 送样，CPO/LPO 路线之争决定下一代封装格局",
        "中际旭创、天孚通信为核心受益，光引擎/无源器件国产化加速",
        "海外云厂资本开支上修，光模块需求能见度延伸至 2027",
      ],
    },
    "PCB/HDI": {
      heading: "PCB / HDI",
      points: [
        "高多层、HDI 加速渗透 AI 服务器，单机价值量显著提升",
        "沪电股份、胜宏科技产能爬坡，高端料号供不应求",
        "材料端覆铜板涨价传导，盈利弹性向头部集中",
      ],
    },
    "HBM/存储": {
      heading: "HBM / 存储",
      points: [
        "HBM3E/HBM4 持续紧缺，封测与材料环节国产突破在即",
        "存储周期上行叠加 AI 拉动，颗粒与模组同步受益",
      ],
    },
    "长鑫·IPO": {
      heading: "长鑫 · IPO",
      points: [
        "长鑫存储 IPO 进程关注度高，国产 DRAM 自主可控里程碑",
        "带动上游设备、材料、封测国产链订单预期",
      ],
    },
    "CPU/GPU": {
      heading: "CPU / GPU",
      points: [
        "国产 GPU 在推理侧加速落地，生态与互联是关键瓶颈",
        "寒武纪、海光信息为 A 股核心算力芯片标的",
      ],
    },
    下游企业: {
      heading: "下游企业",
      points: [
        "AIDC（智算中心）建设放量，服务器整机与液冷需求高增",
        "云厂与运营商 capex 指引是需求的领先指标",
      ],
    },
    算力能源: {
      heading: "算力能源",
      points: [
        "电力是 AI 算力的硬约束，绿电/核电/储能配套需求上升",
        "液冷渗透率快速提升，能效（PUE）成为竞争壁垒",
      ],
    },
    太空算力: {
      heading: "太空算力",
      points: [
        "卫星互联与在轨算力为长期主题，处于早期催化阶段",
        "关注发射成本下降与星座组网进度",
      ],
    },
    核心标的: {
      heading: "核心标的",
      points: [
        "光模块: 中际旭创、天孚通信",
        "PCB: 沪电股份、胜宏科技",
        "AI芯片: 寒武纪、海光信息",
      ],
    },
    估值全景: {
      heading: "估值全景",
      points: [
        "光模块龙头 PEG 仍低（中际旭创 0.19），估值消化最快",
        "PCB/材料标的 PEG 偏高，需以业绩兑现验证",
      ],
    },
    AI新闻: {
      heading: "AI 新闻",
      points: [
        "海外大厂上修 AI 资本开支指引",
        "CPO 产业化时点临近，光电共封进展密集",
        "国产存储与 GPU 自主可控政策持续催化",
      ],
    },
  },
};
