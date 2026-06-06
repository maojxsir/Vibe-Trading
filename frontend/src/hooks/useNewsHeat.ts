import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

const REFRESH_MS = 120_000;

/** Count news headline hits per watchlist name (from Sina feed tagging). */
export function useNewsHeat(names: string[]): {
  hits: Record<string, number>;
  loading: boolean;
  refresh: () => void;
} {
  const key = names.slice().sort().join(",");
  const [hits, setHits] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!key) return;
    setLoading(true);
    try {
      const wire = await api.getNews();
      const list = wire.items.length > 0 ? wire.items : [];
      const counts: Record<string, number> = {};
      for (const n of key.split(",")) counts[n] = 0;
      for (const item of list) {
        const blob = `${item.title} ${item.summary}`;
        for (const name of key.split(",")) {
          if (name && blob.includes(name)) counts[name] = (counts[name] ?? 0) + 1;
        }
        for (const t of item.tickers) {
          if (counts[t] !== undefined) counts[t] = (counts[t] ?? 0) + 1;
        }
      }
      setHits(counts);
    } catch {
      /* keep prior hits */
    } finally {
      setLoading(false);
    }
  }, [key]);

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, REFRESH_MS);
    return () => window.clearInterval(t);
  }, [refresh]);

  return { hits, loading, refresh };
}
