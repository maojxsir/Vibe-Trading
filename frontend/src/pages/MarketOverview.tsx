import { RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { StatCard } from "@/components/dashboard/StatCard";
import { DataTable, type Column } from "@/components/dashboard/DataTable";
import { useMarketOverview } from "@/hooks/useMarketOverview";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import type { StockQuote } from "@/data/types";
import { cn } from "@/lib/utils";

function fmtLivePrice(price: number): string {
  return Number.isFinite(price) ? fmtPrice(price) : "—";
}

function fmtLivePct(pct: number): string {
  return Number.isFinite(pct) ? fmtPct(pct) : "—";
}

function stockColumns(): Column<StockQuote>[] {
  return [
    {
      key: "name",
      header: "名称",
      render: (s) => (
        <div>
          <div className="font-medium text-foreground">{s.name}</div>
          <div className="text-xs text-muted-foreground">{s.tag}</div>
        </div>
      ),
    },
    { key: "price", header: "现价", align: "right", render: (s) => fmtLivePrice(s.price) },
    {
      key: "changePct",
      header: "涨跌",
      align: "right",
      render: (s) => (
        <span className={cn("font-medium", Number.isFinite(s.changePct) ? changeColorClass(s.changePct) : "")}>
          {fmtLivePct(s.changePct)}
        </span>
      ),
    },
    { key: "pe", header: "PE", align: "right", render: (s) => (s.pe == null ? "—" : s.pe.toFixed(1)) },
    {
      key: "peTtm",
      header: "PE(TTM)",
      align: "right",
      render: (s) => (s.peTtm == null ? "—" : s.peTtm.toFixed(2)),
    },
    {
      key: "marketCap",
      header: "市值(亿)",
      align: "right",
      render: (s) => (s.marketCap > 0 ? s.marketCap.toLocaleString("en-US") : "—"),
    },
  ];
}

export function MarketOverview() {
  const { data, loading, refresh } = useMarketOverview();
  const cols = stockColumns();

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="市场总览"
        subtitle="A股大盘·人形机器人 & AI算力 核心标的、实时行情（腾讯, 30s 自动刷新）"
        actions={
          <button
            type="button"
            onClick={refresh}
            className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            刷新
          </button>
        }
      />

      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-foreground">大盘指数</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
          {data.indices.map((idx) => (
            <StatCard
              key={idx.code}
              label={idx.name}
              value={fmtLivePrice(idx.price)}
              changePct={Number.isFinite(idx.changePct) ? idx.changePct : undefined}
            />
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="人形机器人·核心标的" subtitle={data.humanoid.note}>
          <DataTable columns={cols} rows={data.humanoid.stocks} rowKey={(s) => s.code} />
        </Card>
        <Card title="AI算力·核心标的" subtitle={data.aiCompute.note}>
          <DataTable columns={cols} rows={data.aiCompute.stocks} rowKey={(s) => s.code} />
        </Card>
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        更新: {data.updatedAt} · 数据来自{data.source}公开行情, 仅供参考
        {data.stale && <span className="ml-1 text-warning">（行情源暂不可用，部分数据未更新）</span>}
      </p>
    </div>
  );
}
