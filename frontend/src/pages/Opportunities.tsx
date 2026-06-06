import { useMemo, useState } from "react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { DataTable, type Column } from "@/components/dashboard/DataTable";
import { opportunitiesSeed, type Opportunity, type OppStatus } from "@/data/opportunitiesSeed";
import { fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

const STATUS_TONE: Record<OppStatus, "info" | "warning" | "success"> = {
  关注: "info",
  待买: "warning",
  已买: "success",
};

function columns(): Column<Opportunity>[] {
  return [
    { key: "name", header: "标的", render: (o) => <span className="font-medium text-foreground">{o.name} <span className="ml-1 text-xs text-muted-foreground">{o.code}</span></span> },
    { key: "sector", header: "板块", render: (o) => <span className="text-muted-foreground">{o.sector}</span> },
    { key: "trigger", header: "触发逻辑" },
    { key: "target", header: "目标价", align: "right", render: (o) => fmtPrice(o.target) },
    { key: "score", header: "评分", align: "right", render: (o) => <span className={cn("font-medium", o.score >= 85 ? "text-danger" : "text-foreground")}>{o.score}</span> },
    { key: "status", header: "状态", render: (o) => <Badge tone={STATUS_TONE[o.status]}>{o.status}</Badge> },
  ];
}

export function Opportunities() {
  const sectors = useMemo(() => ["全部", ...Array.from(new Set(opportunitiesSeed.map((o) => o.sector.split("·")[0])))], []);
  const [filter, setFilter] = useState("全部");
  const rows = filter === "全部" ? opportunitiesSeed : opportunitiesSeed.filter((o) => o.sector.startsWith(filter));

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader title="机会清单" subtitle="候选标的与触发逻辑、目标价、评分跟踪" />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {sectors.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            className={cn(
              "rounded-md border px-3 py-1 text-sm transition-colors",
              filter === s ? "border-primary bg-primary/10 text-primary" : "bg-card text-muted-foreground hover:text-foreground",
            )}
          >
            {s}
          </button>
        ))}
      </div>

      <Card>
        <DataTable columns={columns()} rows={rows} rowKey={(o) => o.code} />
      </Card>
    </div>
  );
}
