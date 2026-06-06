import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Tabs } from "@/components/dashboard/Tabs";
import { Badge } from "@/components/dashboard/Badge";
import { AlphaFactorBadge, AlphaScoreFootnote } from "@/components/dashboard/AlphaFactorBadge";
import { ModuleStockTable } from "@/components/dashboard/ModuleStockTable";
import { ModuleStockActions } from "@/components/dashboard/ModuleStockActions";
import { aiComputeSeed } from "@/data/aiComputeSeed";
import { collectModuleCodes } from "@/data/types";
import { newsSeed } from "@/data/newsSeed";
import { useAlphaScores } from "@/hooks/useAlphaScores";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { useModuleStocks } from "@/hooks/useModuleStocks";
import { useNewsHeat } from "@/hooks/useNewsHeat";
import { api, type NewsItemWire } from "@/lib/api";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

const AI_NEWS_KEYWORDS = ["算力", "光模块", "AI", "GPU", "CPO", "存储", "服务器", "芯片", "液冷"];

function CoreFourTable({
  alphaLoading,
  alphaScores,
  quotes,
  quotesStale,
}: {
  alphaLoading: boolean;
  alphaScores: ReturnType<typeof useAlphaScores>["scores"];
  quotes: ReturnType<typeof useLiveQuotes>["quotes"];
  quotesStale: boolean;
}) {
  const cols = aiComputeSeed.coreFour;
  const rows: { label: string; cell: (c: (typeof cols)[number]) => React.ReactNode }[] = [
    {
      label: "股价",
      cell: (c) => {
        const q = quotes[c.code];
        const price = q?.price ?? c.price;
        const chg = q?.changePct ?? c.changePct;
        return (
          <span>
            <span className="text-foreground">{fmtPrice(price)}</span>{" "}
            <span className={cn("text-xs", changeColorClass(chg))}>{fmtPct(chg)}</span>
            {quotesStale && !q && <span className="ml-1 text-[10px] text-muted-foreground">seed</span>}
          </span>
        );
      },
    },
    { label: "总市值", cell: (c) => <span className="font-medium text-foreground">{c.cap}</span> },
    { label: "PEG", cell: (c) => <span className={cn(parseFloat(c.peg) < 1 ? "text-success" : "text-danger")}>{c.peg}</span> },
    { label: "消化时间", cell: (c) => c.digest },
    {
      label: "因子分",
      cell: (c) => (
        <AlphaFactorBadge score={alphaScores[c.code]} loading={alphaLoading && !alphaScores[c.code]} />
      ),
    },
    { label: "核心逻辑", cell: (c) => <span className="text-xs text-muted-foreground">{c.logic}</span> },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-muted-foreground">
            <th className="px-3 py-2 text-left font-medium">维度</th>
            {cols.map((c) => (
              <th key={c.code} className="px-3 py-2 text-left font-medium text-foreground">
                {c.name}
                <span className="ml-1 font-normal text-muted-foreground">{c.code}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-border/60 last:border-0">
              <td className="px-3 py-2.5 text-muted-foreground">{r.label}</td>
              {cols.map((c) => (
                <td key={c.code} className="px-3 py-2.5 tabular-nums">{r.cell(c)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AIModuleNews() {
  const [rows, setRows] = useState<NewsItemWire[]>(newsSeed.map((n) => ({ ...n, url: "" })));
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const wire = await api.getNews();
      setRows(wire.items.length > 0 ? wire.items : newsSeed.map((n) => ({ ...n, url: "" })));
    } catch {
      /* keep seed */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filtered = rows.filter((n) => {
    const blob = `${n.title} ${n.summary}`;
    return AI_NEWS_KEYWORDS.some((k) => blob.includes(k)) || n.tickers.some((t) => t.includes("算力") || t.includes("光"));
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">筛选 AI 算力 / 光模块 / 芯片相关资讯（新浪财经）</p>
        <button
          type="button"
          onClick={refresh}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} /> 刷新
        </button>
      </div>
      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground">暂无匹配新闻。</p>
      ) : (
        filtered.slice(0, 12).map((n, i) => (
          <div key={i} className="rounded-lg border border-border/60 p-3">
            <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium text-primary">{n.source}</span>
              <span>·</span>
              <span>{n.time}</span>
            </div>
            {n.url ? (
              <a href={n.url} target="_blank" rel="noopener noreferrer" className="font-medium text-foreground hover:text-primary">
                {n.title}
              </a>
            ) : (
              <p className="font-medium text-foreground">{n.title}</p>
            )}
            {n.summary && <p className="mt-1 text-xs text-muted-foreground">{n.summary}</p>}
            {n.tickers.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {n.tickers.map((t) => (
                  <Badge key={t} tone="neutral">{t}</Badge>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

export function AICompute() {
  const { meta, tabs, sections, overviewIntro } = aiComputeSeed;
  const [active, setActive] = useState(tabs[0]);
  const {
    moduleStocks,
    refreshModule,
    resetModule,
    generating,
    genError,
    refreshedAt,
  } = useModuleStocks("module-stocks:ai-compute", aiComputeSeed.moduleStocks);

  const allCodes = useMemo(
    () => collectModuleCodes(moduleStocks, aiComputeSeed.coreFour.map((c) => c.code)),
    [moduleStocks],
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
  const isNewsTab = active === "AI新闻";
  const isModuleTab = !isOverview && !isNewsTab;

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="AI算力"
        accent="产业链深度分析"
        meta={
          <>
            <Badge tone="primary">{meta.updated}</Badge>
            <Badge tone="info">{meta.layers}</Badge>
            <Badge tone="neutral">{meta.count}</Badge>
            <Badge tone="success">{meta.score}</Badge>
            <span>{meta.sources}</span>
          </>
        }
        actions={
          isModuleTab ? (
            <ModuleStockActions
              onAgentRefresh={() => refreshModule("AI算力", active)}
              agentLoading={generating}
              onRefreshQuotes={refreshQuotes}
              quotesLoading={quotesLoading}
              onReset={() => resetModule(active)}
              refreshedAt={refreshedAt[active]}
              genError={genError}
            />
          ) : undefined
        }
      />

      <Tabs tabs={tabs} active={active} onChange={setActive} className="mb-4" />

      {isOverview ? (
        <div className="space-y-4">
          <Card title="核心四标的的横向对比">
            <CoreFourTable
              alphaLoading={alphaLoading}
              alphaScores={scores}
              quotes={quotes}
              quotesStale={quotesStale}
            />
            <div className="mt-3 border-t pt-3">
              <AlphaScoreFootnote meta={alphaMeta} stale={alphaStale} error={alphaError} />
            </div>
          </Card>
          <Card title="AI算力产业链总览">
            <p className="text-sm leading-relaxed text-muted-foreground">{overviewIntro}</p>
          </Card>
        </div>
      ) : isNewsTab ? (
        <Card title={section?.heading ?? "AI 新闻"}>
          <AIModuleNews />
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
            <div className="mt-3 border-t pt-3 space-y-1">
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
