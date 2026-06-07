import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Tabs } from "@/components/dashboard/Tabs";
import { Badge } from "@/components/dashboard/Badge";
import { AlphaScoreFootnote } from "@/components/dashboard/AlphaFactorBadge";
import { ModuleStockTable } from "@/components/dashboard/ModuleStockTable";
import { ModuleStockActions } from "@/components/dashboard/ModuleStockActions";
import { IndustryNewsPanel } from "@/components/industry/IndustryNewsPanel";
import { ValuationPanel } from "@/components/industry/ValuationPanel";
import { StockChartDrawerProvider } from "@/contexts/StockChartDrawerContext";
import {
  allIndustryChainCodes,
  newsTabConfig,
  OVERVIEW_TAB,
  valuationTabName,
  type IndustryChainConfig,
} from "@/data/industryChainTypes";
import { useAlphaScores } from "@/hooks/useAlphaScores";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { useModuleStocks } from "@/hooks/useModuleStocks";
import { useNewsHeat } from "@/hooks/useNewsHeat";
import { cn } from "@/lib/utils";

export function IndustryChainPage({ config }: { config: IndustryChainConfig }) {
  const valuationTab = valuationTabName(config);
  const newsTab = newsTabConfig(config);
  const [active, setActive] = useState(config.tabs[0]);

  const {
    moduleStocks,
    refreshModule,
    resetModule,
    generating,
    genError,
    refreshedAt,
  } = useModuleStocks(config.storageKey, config.moduleStocks);

  const allCodes = useMemo(
    () => allIndustryChainCodes({ ...config, moduleStocks }),
    [config, moduleStocks],
  );
  const allNames = useMemo(
    () => [...new Set(Object.values(moduleStocks).flat().map((s) => s.name))],
    [moduleStocks],
  );

  const { quotes, stale: quotesStale, refresh: refreshQuotes, loading: quotesLoading } = useLiveQuotes(allCodes);
  const { scores, meta: alphaMeta, stale: alphaStale, loading: alphaLoading, error: alphaError } = useAlphaScores(allCodes);
  const { hits: newsHits } = useNewsHeat(allNames);

  const section = config.sections[active];
  const stocks = moduleStocks[active] ?? [];
  const isOverview = active === OVERVIEW_TAB;
  const isValuationTab = active === valuationTab;
  const isNewsTab = newsTab != null && active === newsTab.tab;
  const isModuleTab = !isOverview && !isValuationTab && !isNewsTab;

  const valuationProps = {
    subtitle: config.valuationSubtitle,
    valuation: config.valuation,
    scores,
    alphaMeta,
    alphaStale,
    alphaLoading,
    alphaError,
    quotes,
    quotesStale,
  };

  return (
    <StockChartDrawerProvider>
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title={config.title}
        accent="产业链深度分析"
        meta={
          <>
            {config.meta.map((item, i) =>
              item.plain || !item.tone ? (
                <span key={i}>{item.text}</span>
              ) : (
                <Badge key={i} tone={item.tone}>{item.text}</Badge>
              ),
            )}
          </>
        }
        actions={
          isModuleTab ? (
            <ModuleStockActions
              onAgentRefresh={() => refreshModule(config.agentModuleName, active)}
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

      <Tabs tabs={config.tabs} active={active} onChange={setActive} className="mb-4" />

      {isOverview ? (
        <div className="space-y-4">
          <ValuationPanel {...valuationProps} />
          <Card title={config.overviewTitle}>
            <p className="text-sm leading-relaxed text-muted-foreground">{config.overviewIntro}</p>
          </Card>
        </div>
      ) : isValuationTab ? (
        <ValuationPanel {...valuationProps} />
      ) : isNewsTab && newsTab ? (
        <Card title={section?.heading ?? newsTab.tab}>
          <IndustryNewsPanel keywords={newsTab.keywords} subtitle={newsTab.subtitle} />
        </Card>
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
    </StockChartDrawerProvider>
  );
}
