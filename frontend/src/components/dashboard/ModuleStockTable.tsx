import { Flame } from "lucide-react";
import { Badge } from "@/components/dashboard/Badge";
import { DataTable, type Column } from "@/components/dashboard/DataTable";
import { AlphaFactorBadge } from "@/components/dashboard/AlphaFactorBadge";
import type { ModuleStock } from "@/data/types";
import type { AlphaStockScore } from "@/hooks/useAlphaScores";
import type { LiveQuote } from "@/hooks/useLiveQuotes";
import { computeModuleHeat, heatLabel, heatTone } from "@/lib/module-heat";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

export function ModuleStockTable({
  rows,
  quotes,
  alphaScores,
  newsHits,
  alphaLoading,
}: {
  rows: ModuleStock[];
  quotes: Record<string, LiveQuote>;
  alphaScores: Record<string, AlphaStockScore>;
  newsHits: Record<string, number>;
  alphaLoading: boolean;
  quotesStale?: boolean;
}) {
  const columns: Column<ModuleStock>[] = [
    {
      key: "name",
      header: "标的",
      render: (r) => (
        <div>
          <span className="font-medium text-foreground">{r.name}</span>
          <span className="ml-1.5 text-xs text-muted-foreground">{r.code}</span>
        </div>
      ),
    },
    {
      key: "industry",
      header: "细分行业",
      render: (r) => <Badge tone="info">{r.industry}</Badge>,
    },
    {
      key: "price",
      header: "现价",
      align: "right",
      render: (r) => {
        const q = quotes[r.code];
        if (q?.price == null) return <span className="text-muted-foreground">—</span>;
        return fmtPrice(q.price);
      },
    },
    {
      key: "chg",
      header: "涨跌",
      align: "right",
      render: (r) => {
        const q = quotes[r.code];
        if (q == null) return <span className="text-muted-foreground">—</span>;
        return <span className={changeColorClass(q.changePct)}>{fmtPct(q.changePct)}</span>;
      },
    },
    {
      key: "alpha",
      header: "因子分",
      align: "right",
      render: (r) => (
        <AlphaFactorBadge score={alphaScores[r.code]} loading={alphaLoading && !alphaScores[r.code]} />
      ),
    },
    {
      key: "heat",
      header: "热度",
      align: "right",
      render: (r) => {
        const heat = computeModuleHeat(
          r.heatBase,
          alphaScores[r.code],
          quotes[r.code],
          newsHits[r.name] ?? 0,
        );
        return (
          <span className="inline-flex items-center justify-end gap-1">
            <Flame className={cn("h-3.5 w-3.5", heat >= 75 ? "text-danger" : heat >= 50 ? "text-warning" : "text-muted-foreground")} />
            <Badge tone={heatTone(heat)}>{heat}</Badge>
            <span className="text-xs text-muted-foreground">{heatLabel(heat)}</span>
          </span>
        );
      },
    },
    {
      key: "logic",
      header: "核心逻辑",
      render: (r) => <span className="text-xs text-muted-foreground">{r.logic}</span>,
    },
  ];

  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">该模块暂无标的映射。</p>;
  }

  return (
    <DataTable columns={columns} rows={rows} rowKey={(r) => r.code} />
  );
}
