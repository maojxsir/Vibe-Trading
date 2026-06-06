import { useCallback, useEffect, useRef, useState } from "react";
import { api, type AlphaStockScoreWire } from "@/lib/api";

const CACHE_KEY = "vt:alpha-scores";
const CACHE_TTL_MS = 6 * 3600 * 1000;

export interface AlphaStockScore {
  code: string;
  composite: number;
  score: number;
  percentile: number;
  label: string;
}

export interface AlphaScoresState {
  scores: Record<string, AlphaStockScore>;
  meta: Record<string, unknown> | null;
  stale: boolean;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

function loadCache(codesKey: string): AlphaScoresState["scores"] | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as {
      codesKey: string;
      expires: number;
      scores: Record<string, AlphaStockScore>;
    };
    if (parsed.codesKey !== codesKey || parsed.expires < Date.now()) return null;
    return parsed.scores;
  } catch {
    return null;
  }
}

function saveCache(codesKey: string, scores: Record<string, AlphaStockScore>) {
  try {
    sessionStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ codesKey, expires: Date.now() + CACHE_TTL_MS, scores }),
    );
  } catch {
    /* quota */
  }
}

function mapWire(wire: AlphaStockScoreWire): Record<string, AlphaStockScore> {
  const out: Record<string, AlphaStockScore> = {};
  for (const [code, row] of Object.entries(wire.scores)) {
    if (!row) continue;
    out[code] = {
      code: row.code,
      composite: row.composite,
      score: row.score,
      percentile: row.percentile,
      label: row.label,
    };
  }
  return out;
}

/** Fetch Alpha Zoo composite factor scores (gtja191·csi300 bench pipeline). */
export function useAlphaScores(codes: string[]): AlphaScoresState {
  const codesKey = codes.join(",");
  const [scores, setScores] = useState<Record<string, AlphaStockScore>>(() => loadCache(codesKey) ?? {});
  const [meta, setMeta] = useState<Record<string, unknown> | null>(null);
  const [stale, setStale] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inflight = useRef(false);

  const refresh = useCallback(async () => {
    const list = codesKey ? codesKey.split(",") : [];
    if (list.length === 0) return;
    if (inflight.current) return;
    inflight.current = true;
    setLoading(true);
    setError(null);
    try {
      const wire = await api.getAlphaScores(list);
      if (wire.status !== "ok" || wire.stale) {
        setStale(true);
        if (wire.error) setError(wire.error);
      } else {
        const mapped = mapWire(wire);
        setScores(mapped);
        setStale(false);
        saveCache(codesKey, mapped);
      }
      setMeta(wire.meta ?? null);
    } catch (e) {
      setStale(true);
      setError(e instanceof Error ? e.message : "因子打分失败");
    } finally {
      setLoading(false);
      inflight.current = false;
    }
  }, [codesKey]);

  useEffect(() => {
    const cached = loadCache(codesKey);
    if (cached && Object.keys(cached).length > 0) {
      setScores(cached);
      setStale(false);
    } else {
      refresh();
    }
  }, [codesKey, refresh]);

  return { scores, meta, stale, loading, error, refresh };
}
