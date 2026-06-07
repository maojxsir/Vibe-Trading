import { Star } from "lucide-react";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { DataTable, type Column } from "@/components/dashboard/DataTable";
import { AlphaFactorBadge, AlphaScoreFootnote } from "@/components/dashboard/AlphaFactorBadge";
import { StockCodeButton, StockSymbolButton } from "@/components/market/StockSymbolButton";
import type { ValuationRow } from "@/data/industryChainTypes";
import type { useAlphaScores } from "@/hooks/useAlphaScores";
import type { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

const RATING_TONE: Record<string, "danger" | "warning" | "info" | "neutral"> = {
  买入: "danger",
  增持: "warning",
  优于大市: "info",
};

function Stars({ n }: { n: number }) {
  return (
    <span className="inline-flex">
      {[0, 1, 2, 3, 4].map((i) => (
        <Star key={i} className={cn("h-3.5 w-3.5", i < n ? "fill-warning text-warning" : "text-muted-foreground/40")} />
      ))}
    </span>
  );
}

function buildColumns(
  alphaScores: ReturnType<typeof useAlphaScores>["scores"],
  alphaLoading: boolean,
  quotes: ReturnType<typeof useLiveQuotes>["quotes"],
  quotesStale: boolean,
): Column<ValuationRow>[] {
  return [
    { key: "name", header: "标的", render: (r) => <StockSymbolButton code={r.code} name={r.name} layout="inline" /> },
    { key: "code", header: "代码", render: (r) => <StockCodeButton code={r.code} name={r.name} /> },
    { key: "module", header: "模块" },
    {
      key: "price",
      header: "现价",
      align: "right",
      render: (r) => {
        const q = quotes[r.code];
        const price = q?.price ?? r.price;
        const chg = q?.changePct;
        return (
          <span>
            <span>{fmtPrice(price)}</span>
            {chg != null && (
              <span className={cn("ml-1 text-xs", changeColorClass(chg))}>{fmtPct(chg)}</span>
            )}
            {quotesStale && !q && <span className="ml-1 text-[10px] text-muted-foreground">seed</span>}
          </span>
        );
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
    { key: "peTtm", header: "PE(TTM)", align: "right", render: (r) => <span className="text-danger">{r.peTtm == null ? "—" : r.peTtm.toFixed(2)}</span> },
    { key: "pb", header: "PB", align: "right", render: (r) => r.pb.toFixed(2) },
    { key: "cap", header: "总市值(亿)", align: "right", render: (r) => r.cap.toFixed(2) },
    { key: "q1Growth", header: "Q1增速", align: "right", render: (r) => <span className={changeColorClass(r.q1Growth)}>{fmtPct(r.q1Growth)}</span> },
    { key: "peg", header: "PEG", align: "right", render: (r) => <span className="text-danger">{r.peg}</span> },
    { key: "digest", header: "演化时间", align: "right" },
    { key: "stars", header: "星级", render: (r) => <Stars n={r.stars} /> },
    { key: "irreplace", header: "不可替代性", render: (r) => <Badge tone="info">{r.irreplace}</Badge> },
    { key: "rating", header: "评级", render: (r) => <Badge tone={RATING_TONE[r.rating] ?? "neutral"}>{r.rating}</Badge> },
  ];
}

export function ValuationPanel({
  subtitle,
  valuation,
  scores,
  alphaMeta,
  alphaStale,
  alphaLoading,
  alphaError,
  quotes,
  quotesStale,
}: {
  subtitle: string;
  valuation: ValuationRow[];
  scores: ReturnType<typeof useAlphaScores>["scores"];
  alphaMeta: ReturnType<typeof useAlphaScores>["meta"];
  alphaStale: boolean;
  alphaLoading: boolean;
  alphaError: string | null;
  quotes: ReturnType<typeof useLiveQuotes>["quotes"];
  quotesStale: boolean;
}) {
  return (
    <Card title="估值全景 · 核心标的的估值一览" subtitle={subtitle}>
      <DataTable
        columns={buildColumns(scores, alphaLoading, quotes, quotesStale)}
        rows={valuation}
        rowKey={(r) => r.code}
      />
      <div className="mt-3 border-t pt-3">
        <AlphaScoreFootnote meta={alphaMeta} stale={alphaStale} error={alphaError} />
      </div>
    </Card>
  );
}
