import { useCallback, useEffect, useRef, useState } from "react";
import { emptyMarketOverview } from "@/data/coreWatchlists";
import type { MarketOverview, StockQuote } from "@/data/types";
import { api } from "@/lib/api";

const REFRESH_MS = 30_000;

function applyQuote<T extends { code: string; name: string; price: number; changePct: number }>(
  row: T,
  quotes: Record<string, { name: string; price: number; change_pct: number }>,
): T {
  const q = quotes[row.code];
  if (!q) return row;
  // Keep curated name/tag/pe/marketCap; only overlay live price and change.
  return { ...row, price: q.price, changePct: q.change_pct };
}

function buildFromWire(wire: Awaited<ReturnType<typeof api.getMarketOverview>>): MarketOverview {
  const base = emptyMarketOverview();
  const { quotes } = wire;
  const stocks = (list: StockQuote[]) => list.map((s) => applyQuote(s, quotes));
  return {
    ...base,
    indices: base.indices.map((idx) => applyQuote(idx, quotes)),
    humanoid: { ...base.humanoid, stocks: stocks(base.humanoid.stocks) },
    aiCompute: { ...base.aiCompute, stocks: stocks(base.aiCompute.stocks) },
    updatedAt: wire.updatedAt || base.updatedAt,
    source: wire.source || base.source,
    stale: wire.stale,
  };
}

export function useMarketOverview() {
  const [data, setData] = useState<MarketOverview>(emptyMarketOverview);
  const [loading, setLoading] = useState(false);
  const timer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const wire = await api.getMarketOverview();
      setData(buildFromWire(wire));
    } catch {
      setData((prev) => ({ ...prev, stale: true }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    timer.current = window.setInterval(refresh, REFRESH_MS);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [refresh]);

  return { data, loading, refresh };
}
