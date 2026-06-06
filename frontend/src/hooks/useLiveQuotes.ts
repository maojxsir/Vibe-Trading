import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { toTencentCode } from "@/lib/cn-market";

const REFRESH_MS = 30_000;

export interface LiveQuote {
  price: number;
  changePct: number;
}

export interface LiveQuotesState {
  quotes: Record<string, LiveQuote>; // keyed by the ORIGINAL code passed in
  stale: boolean;
  updatedAt: string;
  loading: boolean;
  refresh: () => void;
}

/**
 * Poll live quotes for a set of bare A-share codes every 30s.
 *
 * Returns a map keyed by the original (un-prefixed) code so callers can look up
 * by the code they already hold. When the backend is unavailable the map stays
 * empty and ``stale`` is true, so callers fall back to their seed values.
 */
export function useLiveQuotes(codes: string[]): LiveQuotesState {
  const [quotes, setQuotes] = useState<Record<string, LiveQuote>>({});
  const [stale, setStale] = useState(true);
  const [updatedAt, setUpdatedAt] = useState("");
  const [loading, setLoading] = useState(false);

  // Stable key so the effect only re-subscribes when the code set changes.
  const codesKey = codes.join(",");

  const refresh = useCallback(async () => {
    const list = codesKey ? codesKey.split(",") : [];
    if (list.length === 0) return;
    setLoading(true);
    try {
      const tencent = list.map(toTencentCode);
      const wire = await api.getQuotes(tencent);
      if (wire.stale || Object.keys(wire.quotes).length === 0) {
        setStale(true);
      } else {
        const mapped: Record<string, LiveQuote> = {};
        list.forEach((orig) => {
          const q = wire.quotes[toTencentCode(orig)];
          if (q) mapped[orig] = { price: q.price, changePct: q.change_pct };
        });
        setQuotes(mapped);
        setStale(false);
        setUpdatedAt(wire.updatedAt);
      }
    } catch {
      setStale(true);
    } finally {
      setLoading(false);
    }
  }, [codesKey]);

  const timer = useRef<number | null>(null);
  useEffect(() => {
    refresh();
    timer.current = window.setInterval(refresh, REFRESH_MS);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [refresh]);

  return { quotes, stale, updatedAt, loading, refresh };
}
