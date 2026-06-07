// Shared config for 产业链深度分析 pages (Humanoid, AI Compute, future themes).

import { collectModuleCodes, type ModuleStock } from "./types";

export type { ModuleStock };

export interface IndustryChainMetaItem {
  text: string;
  tone?: "primary" | "success" | "info" | "neutral" | "warning" | "danger";
  /** Render as plain text instead of Badge when true */
  plain?: boolean;
}

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

/** Optional tab-specific panels beyond module stock lists. */
export interface IndustryChainSpecialTabs {
  /** Tab label for full valuation table (default: 估值全景) */
  valuation?: string;
  /** Live news feed tab */
  news?: {
    tab: string;
    keywords: string[];
    subtitle?: string;
  };
}

/**
 * Single source of truth for an industry-chain deep-dive page.
 * To add a new theme: create `<theme>Seed.ts` exporting `IndustryChainConfig`, then a one-line page wrapper.
 */
export interface IndustryChainConfig {
  title: string;
  agentModuleName: string;
  storageKey: string;
  meta: IndustryChainMetaItem[];
  tabs: string[];
  overviewIntro: string;
  overviewTitle: string;
  valuationSubtitle: string;
  valuation: ValuationRow[];
  sections: Record<string, ChainSection>;
  moduleStocks: Record<string, ModuleStock[]>;
  specialTabs?: IndustryChainSpecialTabs;
}

export const OVERVIEW_TAB = "总览";
export const DEFAULT_VALUATION_TAB = "估值全景";

export function allIndustryChainCodes(config: IndustryChainConfig): string[] {
  return collectModuleCodes(
    config.moduleStocks,
    config.valuation.map((r) => r.code),
  );
}

export function valuationTabName(config: IndustryChainConfig): string {
  return config.specialTabs?.valuation ?? DEFAULT_VALUATION_TAB;
}

export function newsTabConfig(config: IndustryChainConfig) {
  return config.specialTabs?.news;
}
