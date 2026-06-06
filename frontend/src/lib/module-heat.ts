import type { AlphaStockScore } from "@/hooks/useAlphaScores";
import type { LiveQuote } from "@/hooks/useLiveQuotes";

/** Blend Alpha Zoo factor score, price momentum, and news hits into 0–100 heat. */
export function computeModuleHeat(
  base: number,
  alpha: AlphaStockScore | null | undefined,
  quote: LiveQuote | null | undefined,
  newsHits: number,
): number {
  const factor = alpha?.score ?? base;
  const momentum = quote
    ? Math.min(100, Math.max(0, 50 + quote.changePct * 6))
    : base * 0.6;
  const news = Math.min(100, base * 0.4 + newsHits * 18);
  return Math.round(0.45 * factor + 0.35 * momentum + 0.2 * news);
}

export function heatLabel(score: number): string {
  if (score >= 75) return "高热度";
  if (score >= 50) return "中热度";
  return "低热度";
}

export type HeatTone = "danger" | "warning" | "neutral";

export function heatTone(score: number): HeatTone {
  if (score >= 75) return "danger";
  if (score >= 50) return "warning";
  return "neutral";
}
