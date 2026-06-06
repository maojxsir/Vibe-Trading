// Curated seed for the 逻辑链 (logic chain) page — mirrors screenshot 4.
// Node kinds map to colours: trigger=red, transmit=yellow, sector=purple, target=green.

import type { Edge, Node } from "@xyflow/react";

export type ChainKind = "trigger" | "transmit" | "sector" | "target";

export interface ChainNodeData extends Record<string, unknown> {
  label: string;
  desc: string;
  kind: ChainKind;
}

export type ChainNode = Node<ChainNodeData, "chainNode">;

export const KIND_LABEL: Record<ChainKind, string> = {
  trigger: "触发因素",
  transmit: "传导逻辑",
  sector: "受益板块",
  target: "具体标的",
};

// Tailwind classes per kind (border + subtle background). Works in light/dark.
export const KIND_CLASS: Record<ChainKind, string> = {
  trigger: "border-red-500 bg-red-500/10",
  transmit: "border-amber-400 bg-amber-400/10",
  sector: "border-purple-500 bg-purple-500/10",
  target: "border-emerald-500 bg-emerald-500/10",
};

export const KIND_DOT: Record<ChainKind, string> = {
  trigger: "bg-red-500",
  transmit: "bg-amber-400",
  sector: "bg-purple-500",
  target: "bg-emerald-500",
};

// Top preset chains (chips).
export const CHAIN_PRESETS: string[] = [
  "算力租赁暴涨链",
  "霍尔木兹封锁→能源危机",
  "石油美元崩溃→人民币崛起",
  "中美AI竞争→西芯东电",
  "AI泡沫→次贷2.0(2028)",
  "中国能源独立→制造业称霸",
  "白银硬大战→定价权东移",
  "文生视频→内容产业重构",
  "DeepSeek→美元霸权动摇",
  "特朗普控→信用耗尽",
  "日本五条→订单东移中国",
  "A股新蓄水池→财富大转移",
  "美国衰落→总督模式接守",
];

export const DEFAULT_CHAIN = "中美AI竞争→西芯东电";

// Default graph for the selected preset (screenshot 4).
export const defaultNodes: ChainNode[] = [
  { id: "t1", type: "chainNode", position: { x: 0, y: 40 }, data: { kind: "trigger", label: "23倍资金仅换2.7%领先", desc: "美AI投资2859亿 vs 中国124亿, 模型差距300倍→2.7%" } },
  { id: "t2", type: "chainNode", position: { x: 0, y: 220 }, data: { kind: "trigger", label: "H200解禁出口", desc: "H200已输先→中国算力分子: 美出芯, 中出电" } },
  { id: "t3", type: "chainNode", position: { x: 0, y: 400 }, data: { kind: "trigger", label: "美国AIDC建不起", desc: "网络瓶颈→美国500-800亿元 vs 中国500-800亿元" } },
  { id: "m1", type: "chainNode", position: { x: 340, y: 130 }, data: { kind: "transmit", label: "AI竞争转向性价比", desc: "模型参数不再决定胜负→应用规模/成本效率/人才储备成为关键" } },
  { id: "m2", type: "chainNode", position: { x: 340, y: 330 }, data: { kind: "transmit", label: "中国职场AI采用率>80%", desc: "美国仅7000万人用AI/快乐教育→应试; 中国全民用AI" } },
  { id: "s1", type: "chainNode", position: { x: 680, y: 40 }, data: { kind: "sector", label: "中国算力基础设施", desc: "全球算力设施向中国转移→逐步替代石油美元" } },
  { id: "s2", type: "chainNode", position: { x: 680, y: 220 }, data: { kind: "sector", label: "开源模型出海", desc: "中国token占七十几万亿, 开源+低价token全球" } },
  { id: "s3", type: "chainNode", position: { x: 680, y: 400 }, data: { kind: "sector", label: "光模块(国产化)", desc: "Google TPU路线→光连可避免英伟达, 中芯可代工" } },
  { id: "g1", type: "chainNode", position: { x: 1020, y: 320 }, data: { kind: "target", label: "中际旭创", desc: "光模块受益核心标的" } },
];

export const defaultEdges: Edge[] = [
  { id: "e-t1-m1", source: "t1", target: "m1" },
  { id: "e-t2-m1", source: "t2", target: "m1" },
  { id: "e-t2-m2", source: "t2", target: "m2" },
  { id: "e-t3-m2", source: "t3", target: "m2" },
  { id: "e-m1-s1", source: "m1", target: "s1" },
  { id: "e-m1-s2", source: "m1", target: "s2" },
  { id: "e-m2-s2", source: "m2", target: "s2" },
  { id: "e-m1-s3", source: "m1", target: "s3" },
  { id: "e-s3-g1", source: "s3", target: "g1" },
];
