import { useEffect, useState } from "react";
import { api, type PriceBar } from "@/lib/api";

const TTL_MS = 5 * 60 * 1000;
const cache = new Map<string, { bars: PriceBar[]; at: number; source: string }>();

export function useStockKline(code: string | null) {
  const [bars, setBars] = useState<PriceBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState("");

  useEffect(() => {
    if (!code) {
      setBars([]);
      setError(null);
      setSource("");
      return;
    }

    const hit = cache.get(code);
    if (hit && Date.now() - hit.at < TTL_MS) {
      setBars(hit.bars);
      setSource(hit.source);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getKline(code)
      .then((res) => {
        if (cancelled) return;
        if (res.stale || res.bars.length === 0) {
          setBars([]);
          setSource(res.source || "");
          setError(res.error ?? "K 线暂不可用，请检查行情数据源配置");
          return;
        }
        cache.set(code, { bars: res.bars, at: Date.now(), source: res.source });
        setBars(res.bars);
        setSource(res.source);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setBars([]);
        setError(err instanceof Error ? err.message : "加载失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  return { bars, loading, error, source };
}
