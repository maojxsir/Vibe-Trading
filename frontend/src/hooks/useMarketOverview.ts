import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { marketSeed } from "@/data/marketSeed";
import type { MarketOverview, StockQuote } from "@/data/types";

const REFRESH_MS = 30_000;

// Overlay live price/changePct from the backend onto the curated seed (which
// keeps names/tags/PE/marketCap). Any code missing from the live payload keeps
// its seed values, so a partial upstream failure never blanks a row.
function mergeQuotes(
  seed: MarketOverview,
  wire: Awaited<ReturnType<typeof api.getMarketOverview>>,
): MarketOverview {
  const apply = (stocks: StockQuote[]): StockQuote[] =>
    stocks.map((s) => {
      const q = wire.quotes[s.code];
      return q ? { ...s, price: q.price, changePct: q.change_pct } : s;
    });
  return {
    ...seed,
    indices: seed.indices.map((idx) => {
      const q = wire.quotes[idx.code];
      return q ? { ...idx, price: q.price, changePct: q.change_pct } : idx;
    }),
    humanoid: { ...seed.humanoid, stocks: apply(seed.humanoid.stocks) },
    aiCompute: { ...seed.aiCompute, stocks: apply(seed.aiCompute.stocks) },
    updatedAt: wire.updatedAt || seed.updatedAt,
    source: wire.source || seed.source,
    stale: wire.stale,
  };
}

export function useMarketOverview() {
  const [data, setData] = useState<MarketOverview>(marketSeed);
  const [loading, setLoading] = useState(false);
  const timer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const wire = await api.getMarketOverview();
      // Keep seed when upstream is stale/empty so the page never blanks out.
      if (wire.stale || Object.keys(wire.quotes).length === 0) {
        setData({ ...marketSeed, stale: true, updatedAt: wire.updatedAt || marketSeed.updatedAt });
      } else {
        setData(mergeQuotes(marketSeed, wire));
      }
    } catch {
      setData({ ...marketSeed, stale: true });
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
