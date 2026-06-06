import { useState } from "react";
import { RefreshCw, Star } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Tabs } from "@/components/dashboard/Tabs";
import { Badge } from "@/components/dashboard/Badge";
import { DataTable, type Column } from "@/components/dashboard/DataTable";
import { humanoidSeed, type ValuationRow } from "@/data/humanoidSeed";
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

function valuationColumns(): Column<ValuationRow>[] {
  return [
    { key: "name", header: "标的", render: (r) => <span className="font-medium text-foreground">{r.name}</span> },
    { key: "code", header: "代码", render: (r) => <span className="text-muted-foreground">{r.code}</span> },
    { key: "module", header: "模块" },
    { key: "price", header: "现价", align: "right", render: (r) => fmtPrice(r.price) },
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

export function Humanoid() {
  const { meta, tabs, sections, valuation, valuationSubtitle } = humanoidSeed;
  const [active, setActive] = useState("估值全景");

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
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <RefreshCw className="h-4 w-4" />
            刷新行情
          </button>
        }
      />

      <Tabs tabs={tabs} active={active} onChange={setActive} className="mb-4" />

      {active === "估值全景" || active === "总览" ? (
        <Card title="估值全景 · 核心标的的估值一览" subtitle={valuationSubtitle}>
          <DataTable columns={valuationColumns()} rows={valuation} rowKey={(r) => r.code} />
        </Card>
      ) : (
        <Card title={sections[active]?.heading ?? active}>
          <ul className="space-y-2">
            {(sections[active]?.points ?? ["内容整理中"]).map((p, i) => (
              <li key={i} className="flex gap-2 text-sm text-muted-foreground">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
