import { useEffect, useMemo, useState } from "react";
import { api, type SymbolSearchResultWire } from "@/lib/api";

export interface SymbolSearchState {
  results: SymbolSearchResultWire[];
  loading: boolean;
  error: string;
}

export function useSymbolSearch(query: string, boostCodes: string[] = [], limit = 12): SymbolSearchState {
  const [results, setResults] = useState<SymbolSearchResultWire[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const boostKey = useMemo(() => boostCodes.join(","), [boostCodes]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const wire = await api.searchSymbols(query.trim(), boostKey ? boostKey.split(",") : [], limit);
        if (cancelled) return;
        setResults(wire.results ?? []);
        setError(wire.status === "error" ? wire.message || "标的库暂不可用" : "");
      } catch (err) {
        if (cancelled) return;
        setResults([]);
        setError(err instanceof Error ? err.message : "标的库暂不可用");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 200);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [boostKey, limit, query]);

  return { results, loading, error };
}
