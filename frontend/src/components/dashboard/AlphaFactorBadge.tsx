import { Loader2 } from "lucide-react";
import { Badge } from "@/components/dashboard/Badge";
import type { AlphaStockScore } from "@/hooks/useAlphaScores";

const TONE: Record<string, "success" | "warning" | "neutral"> = {
  偏强: "success",
  中性: "warning",
  偏弱: "neutral",
};

export function AlphaFactorBadge({
  score,
  loading,
}: {
  score?: AlphaStockScore | null;
  loading?: boolean;
}) {
  if (loading) {
    return <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" aria-label="加载因子分" />;
  }
  if (!score) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Badge tone={TONE[score.label] ?? "neutral"}>{score.score}</Badge>
      <span className="text-xs text-muted-foreground">{score.label}</span>
    </span>
  );
}

export function AlphaScoreFootnote({
  meta,
  stale,
  error,
}: {
  meta: Record<string, unknown> | null;
  stale: boolean;
  error: string | null;
}) {
  if (error && stale) {
    return (
      <p className="text-xs text-muted-foreground">
        因子分不可用（{error}）。需后端运行且配置 TUSHARE_TOKEN；也可在{" "}
        <a href="/alpha-zoo/bench?zoo=gtja191&universe=csi300&period=2024-2025" className="text-primary hover:underline">
          Alpha Zoo bench
        </a>{" "}
        手动跑分。
      </p>
    );
  }
  if (!meta) return null;
  const zoo = String(meta.zoo ?? "gtja191");
  const universe = String(meta.universe ?? "csi300");
  const period = String(meta.period ?? "2024-2025");
  const n = meta.n_alphas_used ?? "—";
  const asOf = meta.as_of ? ` · 信号日 ${meta.as_of}` : "";
  return (
    <p className="text-xs text-muted-foreground">
      Alpha Zoo 因子分：{zoo}·{universe} bench（{period}），合成 {String(n)} 个 alive 因子{asOf}。
      CSI300 截面百分位，越高表示多因子信号越强。
    </p>
  );
}
