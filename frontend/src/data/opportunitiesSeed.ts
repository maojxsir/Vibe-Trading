// Curated seed for the 机会清单 (opportunity list) page.

export type OppStatus = "关注" | "待买" | "已买";

export interface Opportunity {
  name: string;
  code: string;
  sector: string;
  trigger: string;
  target: number;
  score: number; // 0-100
  status: OppStatus;
}

export const opportunitiesSeed: Opportunity[] = [
  { name: "中际旭创", code: "300308", sector: "AI算力·光模块", trigger: "1.6T 放量 + PEG<1", target: 1500, score: 92, status: "关注" },
  { name: "天孚通信", code: "300394", sector: "AI算力·CPO", trigger: "CPO 材料受益", target: 560, score: 85, status: "待买" },
  { name: "沪电股份", code: "002463", sector: "AI算力·PCB", trigger: "高端 PCB 扩产提速", target: 150, score: 80, status: "关注" },
  { name: "拓普集团", code: "601689", sector: "人形机器人·执行器", trigger: "丝杠国产突破", target: 75, score: 78, status: "待买" },
  { name: "寒武纪", code: "688256", sector: "AI算力·AI芯片", trigger: "国产推理放量", target: 1500, score: 70, status: "关注" },
];
