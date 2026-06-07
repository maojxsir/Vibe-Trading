// Curated research content for the AI算力 (AI compute) industry-chain page.

import type { ChainSection, IndustryChainConfig, ModuleStock, ValuationRow } from "./industryChainTypes";

export type { ModuleStock, ValuationRow };

const AI_NEWS_KEYWORDS = ["算力", "光模块", "AI", "GPU", "CPO", "存储", "服务器", "芯片", "液冷"];

const valuation: ValuationRow[] = [
  { name: "中际旭创", code: "300308", module: "光模块", price: 1275.0, peTtm: 45.2, pb: 12.5, cap: 14148, q1Growth: 85.0, peg: "0.19", digest: "0.4年", stars: 5, irreplace: "global", rating: "买入" },
  { name: "沪电股份", code: "002463", module: "PCB/HDI", price: 129.8, peTtm: 32.1, pb: 8.2, cap: 2496, q1Growth: 42.0, peg: "0.96", digest: "1.4年", stars: 4, irreplace: "capacity", rating: "买入" },
  { name: "胜宏科技", code: "300476", module: "PCB/HDI", price: 353.44, peTtm: 58.0, pb: 15.3, cap: 3058, q1Growth: 55.0, peg: "3.80", digest: "4.8年", stars: 3, irreplace: "tech", rating: "增持" },
  { name: "天孚通信", code: "300394", module: "光模块", price: 497.38, peTtm: 52.0, pb: 18.1, cap: 3868, q1Growth: 48.0, peg: "3.80", digest: "4.7年", stars: 4, irreplace: "tech", rating: "增持" },
  { name: "寒武纪", code: "688256", module: "CPU/GPU", price: 580.0, peTtm: null, pb: 22.0, cap: 2400, q1Growth: 120.0, peg: "—", digest: "—", stars: 3, irreplace: "platform", rating: "增持" },
  { name: "海光信息", code: "688041", module: "CPU/GPU", price: 145.0, peTtm: 185.0, pb: 14.5, cap: 3200, q1Growth: 65.0, peg: "2.85", digest: "2.9年", stars: 4, irreplace: "platform", rating: "买入" },
];

const sections: Record<string, ChainSection> = {
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
};

const moduleStocks: Record<string, ModuleStock[]> = {
  光模块: [
    { name: "中际旭创", code: "300308", industry: "光模块龙头", module: "光模块", heatBase: 92, logic: "800G/1.6T 放量，全球份额第一" },
    { name: "天孚通信", code: "300394", industry: "光无源器件", module: "光模块", heatBase: 88, logic: "CPO 光引擎材料核心供应商" },
    { name: "新易盛", code: "300502", industry: "光模块", module: "光模块", heatBase: 82, logic: "海外客户拓展 + 高速模块上量" },
    { name: "光迅科技", code: "002281", industry: "光器件", module: "光模块", heatBase: 74, logic: "国企背景 + 硅光/CPO 布局" },
  ],
  "PCB/HDI": [
    { name: "沪电股份", code: "002463", industry: "AI 服务器 PCB", module: "PCB/HDI", heatBase: 85, logic: "高端多层板扩产，AI 服务器核心供应商" },
    { name: "胜宏科技", code: "300476", industry: "HDI/高多层", module: "PCB/HDI", heatBase: 83, logic: "AI 显卡/服务器 PCB 份额提升" },
    { name: "深南电路", code: "002916", industry: "封装基板", module: "PCB/HDI", heatBase: 78, logic: "IC 载板 + 数据中心 PCB 双轮" },
    { name: "生益科技", code: "600183", industry: "覆铜板", module: "PCB/HDI", heatBase: 70, logic: "上游 CCL 涨价传导，高端料号紧缺" },
  ],
  "HBM/存储": [
    { name: "兆易创新", code: "603986", industry: "NOR/DRAM", module: "HBM/存储", heatBase: 76, logic: "存储周期上行 + 车规/工控需求" },
    { name: "北京君正", code: "300223", industry: "存储芯片", module: "HBM/存储", heatBase: 72, logic: "利基型 DRAM 国产替代" },
    { name: "江波龙", code: "301308", industry: "存储模组", module: "HBM/存储", heatBase: 68, logic: "模组厂受益存储涨价与 AI 拉动" },
    { name: "佰维存储", code: "688525", industry: "存储模组", module: "HBM/存储", heatBase: 65, logic: "嵌入式存储 + 信创放量" },
  ],
  "长鑫·IPO": [
    { name: "雅克科技", code: "002409", industry: "前驱体/材料", module: "长鑫链", heatBase: 80, logic: "长鑫存储上游材料核心供应商" },
    { name: "鼎龙股份", code: "300054", industry: "CMP/光刻胶", module: "长鑫链", heatBase: 75, logic: "国产半导体材料平台化" },
    { name: "北方华创", code: "002371", industry: "刻蚀/沉积", module: "长鑫链", heatBase: 78, logic: "存储扩产拉动的设备龙头" },
    { name: "中微公司", code: "688012", industry: "刻蚀设备", module: "长鑫链", heatBase: 74, logic: "先进制程/存储产线设备" },
  ],
  "CPU/GPU": [
    { name: "寒武纪", code: "688256", industry: "AI 芯片", module: "CPU/GPU", heatBase: 86, logic: "国产推理芯片放量，生态加速" },
    { name: "海光信息", code: "688041", industry: "CPU/GPU", module: "CPU/GPU", heatBase: 84, logic: "x86 兼容 + 深算 DCU 双产品线" },
    { name: "景嘉微", code: "300474", industry: "GPU", module: "CPU/GPU", heatBase: 68, logic: "特种 GPU + 民用拓展" },
  ],
  下游企业: [
    { name: "浪潮信息", code: "000977", industry: "AI 服务器", module: "下游", heatBase: 82, logic: "国内 AI 服务器龙头，绑定头部云厂" },
    { name: "工业富联", code: "601138", industry: "服务器代工", module: "下游", heatBase: 80, logic: "全球服务器 ODM，AI 服务器放量" },
    { name: "中科曙光", code: "603019", industry: "智算中心", module: "下游", heatBase: 77, logic: "国产算力整机 + 算力运营" },
  ],
  算力能源: [
    { name: "润泽科技", code: "300442", industry: "IDC/AIDC", module: "算力能源", heatBase: 79, logic: "京津冀/长三角智算中心稀缺资源" },
    { name: "英维克", code: "002837", industry: "液冷", module: "算力能源", heatBase: 76, logic: "AI 服务器液冷渗透率提升" },
    { name: "宝信软件", code: "600845", industry: "数据中心", module: "算力能源", heatBase: 70, logic: "钢铁/央企 IDC + 算力调度" },
  ],
  太空算力: [
    { name: "中国卫星", code: "600118", industry: "卫星制造", module: "太空算力", heatBase: 62, logic: "低轨星座组网，在轨算力远期主题" },
    { name: "航天电子", code: "600879", industry: "航天电子", module: "太空算力", heatBase: 58, logic: "卫星载荷与测控，星座配套" },
  ],
  核心标的: [
    { name: "中际旭创", code: "300308", industry: "光模块", module: "光模块", heatBase: 92, logic: "产业链核心龙头" },
    { name: "沪电股份", code: "002463", industry: "PCB", module: "PCB/HDI", heatBase: 85, logic: "AI 服务器 PCB 核心" },
    { name: "寒武纪", code: "688256", industry: "AI 芯片", module: "CPU/GPU", heatBase: 86, logic: "国产算力芯片" },
    { name: "浪潮信息", code: "000977", industry: "服务器", module: "下游", heatBase: 82, logic: "算力落地终端" },
  ],
  估值全景: [
    { name: "中际旭创", code: "300308", industry: "光模块", module: "光模块", heatBase: 92, logic: "PEG 最低，估值消化最快" },
    { name: "天孚通信", code: "300394", industry: "光器件", module: "光模块", heatBase: 88, logic: "CPO 材料弹性" },
    { name: "沪电股份", code: "002463", industry: "PCB", module: "PCB/HDI", heatBase: 85, logic: "业绩兑现能见度好" },
    { name: "胜宏科技", code: "300476", industry: "PCB", module: "PCB/HDI", heatBase: 83, logic: "高估值需业绩验证" },
    { name: "寒武纪", code: "688256", industry: "AI 芯片", module: "CPU/GPU", heatBase: 86, logic: "高成长溢价" },
    { name: "海光信息", code: "688041", industry: "CPU/GPU", module: "CPU/GPU", heatBase: 84, logic: "平台型算力标的" },
  ],
};

export const aiComputeConfig: IndustryChainConfig = {
  title: "AI算力",
  agentModuleName: "AI算力",
  storageKey: "module-stocks:ai-compute",
  meta: [
    { text: "2026-05-27 更新", tone: "primary" },
    { text: "5层14环节", tone: "info" },
    { text: "16只标的", tone: "neutral" },
    { text: "L1评分 83.8", tone: "success" },
    { text: "数据来源: 1171条研报 + LightCounting + SemiAnalysis + Bernstein", plain: true },
  ],
  tabs: [
    "总览", "光模块", "PCB/HDI", "HBM/存储", "长鑫·IPO", "CPU/GPU",
    "下游企业", "算力能源", "太空算力", "核心标的", "估值全景", "AI新闻",
  ],
  overviewIntro:
    "AI 算力产业链覆盖光模块、PCB/HDI、HBM/存储、CPU/GPU、算力能源等 5 层 14 环节。当前主线集中在光模块（CPO 升级）与高端 PCB，海外资本开支维持高增，国产替代提速。",
  overviewTitle: "AI算力产业链总览",
  valuationSubtitle: "16 家核心标的的实时估值 | 数据更新: 2026-05-27",
  valuation,
  sections,
  moduleStocks,
  specialTabs: {
    valuation: "估值全景",
    news: {
      tab: "AI新闻",
      keywords: AI_NEWS_KEYWORDS,
      subtitle: "筛选 AI 算力 / 光模块 / 芯片相关资讯（新浪财经）",
    },
  },
};

export const aiComputeSeed = aiComputeConfig;
