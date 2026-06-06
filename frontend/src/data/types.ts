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
  marketCap: number; // 亿 (100M CNY)
}

export interface MarketOverview {
  indices: IndexQuote[];
  humanoid: { note: string; stocks: StockQuote[] };
  aiCompute: { note: string; stocks: StockQuote[] };
  updatedAt: string;
  source: string;
  stale?: boolean; // true when served from the seed/cache fallback
}
