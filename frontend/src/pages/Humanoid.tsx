import { useMemo, useState } from "react";
import { RefreshCw, Star } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Tabs } from "@/components/dashboard/Tabs";
import { Badge } from "@/components/dashboard/Badge";
import { DataTable, type Column } from "@/components/dashboard/DataTable";
import { AlphaFactorBadge, AlphaScoreFootnote } from "@/components/dashboard/AlphaFactorBadge";
import { ModuleStockTable } from "@/components/dashboard/ModuleStockTable";
import { ModuleStockActions } from "@/components/dashboard/ModuleStockActions";
import { humanoidSeed, type ValuationRow } from "@/data/humanoidSeed";
import { collectModuleCodes } from "@/data/types";
import { useAlphaScores } from "@/hooks/useAlphaScores";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { useModuleStocks } from "@/hooks/useModuleStocks";
import { useNewsHeat } from "@/hooks/useNewsHeat";
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

function valuationColumns(
  alphaScores: ReturnType<typeof useAlphaScores>["scores"],
  alphaLoading: boolean,
  quotes: ReturnType<typeof useLiveQuotes>["quotes"],
  quotesStale: boolean,
): Column<ValuationRow>[] {
  return [
    { key: "name", header: "标的", render: (r) => <span className="font-medium text-foreground">{r.name}</span> },
    { key: "code", header: "代码", render: (r) => <span className="text-muted-foreground">{r.code}</span> },
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

function ValuationPanel({
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
        columns={valuationColumns(scores, alphaLoading, quotes, quotesStale)}
        rows={valuation}
        rowKey={(r) => r.code}
      />
      <div className="mt-3 border-t pt-3">
        <AlphaScoreFootnote meta={alphaMeta} stale={alphaStale} error={alphaError} />
      </div>
    </Card>
  );
}

export function Humanoid() {
  const { meta, tabs, sections, valuation, valuationSubtitle, overviewIntro } = humanoidSeed;
  const [active, setActive] = useState(tabs[0]);
  const {
    moduleStocks,
    refreshModule,
    resetModule,
    generating,
    genError,
    refreshedAt,
  } = useModuleStocks("module-stocks:humanoid", humanoidSeed.moduleStocks);

  const allCodes = useMemo(
    () => collectModuleCodes(moduleStocks, valuation.map((r) => r.code)),
    [moduleStocks, valuation],
  );
  const allNames = useMemo(
    () => [...new Set(Object.values(moduleStocks).flat().map((s) => s.name))],
    [moduleStocks],
  );

  const { quotes, stale: quotesStale, refresh: refreshQuotes, loading: quotesLoading } = useLiveQuotes(allCodes);
  const { scores, meta: alphaMeta, stale: alphaStale, loading: alphaLoading, error: alphaError } = useAlphaScores(allCodes);
  const { hits: newsHits } = useNewsHeat(allNames);

  const section = sections[active];
  const stocks = moduleStocks[active] ?? [];
  const isOverview = active === "总览";
  const isValuationTab = active === "估值全景";
  const isModuleTab = !isOverview && !isValuationTab;

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="人形机器人"
        accent="产业链深度分析"
        meta={
          <>
            <span>{meta.based}</span>
            <Badge tone="primary">{meta.dataDate}</Badge>
            <Badge tone="success">{meta.marketTime}</Badge>
          </>
        }
        actions={
          isModuleTab ? (
            <ModuleStockActions
              onAgentRefresh={() => refreshModule("人形机器人", active)}
              agentLoading={generating}
              onRefreshQuotes={refreshQuotes}
              quotesLoading={quotesLoading}
              onReset={() => resetModule(active)}
              refreshedAt={refreshedAt[active]}
              genError={genError}
            />
          ) : !isOverview ? (
            <button
              type="button"
              onClick={refreshQuotes}
              disabled={quotesLoading}
              className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
            >
              <RefreshCw className={cn("h-4 w-4", quotesLoading && "animate-spin")} />
              刷新行情
            </button>
          ) : undefined
        }
      />

      <Tabs tabs={tabs} active={active} onChange={setActive} className="mb-4" />

      {isOverview ? (
        <div className="space-y-4">
          <ValuationPanel
            subtitle={valuationSubtitle}
            valuation={valuation}
            scores={scores}
            alphaMeta={alphaMeta}
            alphaStale={alphaStale}
            alphaLoading={alphaLoading}
            alphaError={alphaError}
            quotes={quotes}
            quotesStale={quotesStale}
          />
          <Card title="人形机器人产业链总览">
            <p className="text-sm leading-relaxed text-muted-foreground">{overviewIntro}</p>
          </Card>
        </div>
      ) : isValuationTab ? (
        <ValuationPanel
          subtitle={valuationSubtitle}
          valuation={valuation}
          scores={scores}
          alphaMeta={alphaMeta}
          alphaStale={alphaStale}
          alphaLoading={alphaLoading}
          alphaError={alphaError}
          quotes={quotes}
          quotesStale={quotesStale}
        />
      ) : (
        <div className="space-y-4">
          {section && section.points.length > 0 && (
            <Card title={`${section.heading} · 产业要点`} subtitle="研报与产业链梳理">
              <ul className="space-y-2">
                {section.points.map((p, i) => (
                  <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
          <Card
            title={`${section?.heading ?? active} · 模块标的`}
            subtitle="热度 = Alpha Zoo 因子分 + 涨跌幅动量 + 新闻提及（Vibe-Trading 实时合成）"
          >
            <ModuleStockTable
              rows={stocks}
              quotes={quotes}
              alphaScores={scores}
              newsHits={newsHits}
              alphaLoading={alphaLoading}
              quotesStale={quotesStale}
            />
            <div className="mt-3 space-y-1 border-t pt-3">
              <AlphaScoreFootnote meta={alphaMeta} stale={alphaStale} error={alphaError} />
              <p className="text-xs text-muted-foreground">
                标的列表：默认 seed，可 Agent 手动刷新并本地缓存 · 行情 30s{quotesStale ? "（seed/离线）" : ""} · 新闻 2min
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
