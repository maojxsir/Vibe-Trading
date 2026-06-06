import { useState } from "react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Tabs } from "@/components/dashboard/Tabs";
import { Badge } from "@/components/dashboard/Badge";
import { aiComputeSeed } from "@/data/aiComputeSeed";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

function CoreFourTable() {
  const cols = aiComputeSeed.coreFour;
  const rows: { label: string; cell: (c: (typeof cols)[number]) => React.ReactNode }[] = [
    {
      label: "股价",
      cell: (c) => (
        <span>
          <span className="text-foreground">{fmtPrice(c.price)}</span>{" "}
          <span className={cn("text-xs", changeColorClass(c.changePct))}>{fmtPct(c.changePct)}</span>
        </span>
      ),
    },
    { label: "总市值", cell: (c) => <span className="font-medium text-foreground">{c.cap}</span> },
    { label: "PEG", cell: (c) => <span className={cn(parseFloat(c.peg) < 1 ? "text-success" : "text-danger")}>{c.peg}</span> },
    { label: "消化时间", cell: (c) => c.digest },
    { label: "核心逻辑", cell: (c) => <span className="text-xs text-muted-foreground">{c.logic}</span> },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-muted-foreground">
            <th className="px-3 py-2 text-left font-medium">维度</th>
            {cols.map((c) => (
              <th key={c.name} className="px-3 py-2 text-left font-medium text-foreground">{c.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-border/60 last:border-0">
              <td className="px-3 py-2.5 text-muted-foreground">{r.label}</td>
              {cols.map((c) => (
                <td key={c.name} className="px-3 py-2.5 tabular-nums">{r.cell(c)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AICompute() {
  const { meta, tabs, sections, overviewIntro } = aiComputeSeed;
  const [active, setActive] = useState(tabs[0]);

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
      />

      <Tabs tabs={tabs} active={active} onChange={setActive} className="mb-4" />

      {active === "总览" ? (
        <div className="space-y-4">
          <Card title="核心四标的的横向对比">
            <CoreFourTable />
          </Card>
          <Card title="AI算力产业链总览">
            <p className="text-sm leading-relaxed text-muted-foreground">{overviewIntro}</p>
          </Card>
        </div>
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
