// Seed/runtime data shapes for the CN A-share research workbench pages.

export interface IndexQuote {
  name: string;
  code: string;
  price: number;
  changePct: number;
}

export interface StockQuote {
  name: string;
  code: string;
  tag: string; // industry / role label shown under the name
  price: number;
  changePct: number;
  pe: number | null;
  peTtm: number | null;
  marketCap: number; // 亿 (100M CNY)
}

export interface MarketOverview {
  indices: IndexQuote[];
  humanoid: { note: string; stocks: StockQuote[] };
  aiCompute: { note: string; stocks: StockQuote[] };
  updatedAt: string;
  source: string;
  stale?: boolean; // true when live quotes are unavailable or partial
}

/** Industry-chain module watchlist row (AI算力 / 人形机器人 tabs). */
export interface ModuleStock {
  name: string;
  code: string;
  industry: string;
  module: string;
  heatBase: number;
  logic: string;
}

export function collectModuleCodes(
  moduleStocks: Record<string, ModuleStock[]>,
  extra: string[] = [],
): string[] {
  const set = new Set<string>(extra);
  for (const rows of Object.values(moduleStocks)) {
    for (const r of rows) set.add(r.code);
  }
  return [...set];
}
