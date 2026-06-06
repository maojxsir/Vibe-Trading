import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { eventsSeed, type EventDir } from "@/data/eventsSeed";
import { cn } from "@/lib/utils";

const DIR_TONE: Record<EventDir, "danger" | "success" | "neutral"> = {
  利好: "danger",
  利空: "success",
  中性: "neutral",
};

export function Events() {
  return (
    <div className="mx-auto max-w-5xl p-6">
      <PageHeader title="事件概率" subtitle="关键事件的发生概率、影响标的与方向" />

      <Card>
        <div className="space-y-4">
          {eventsSeed.map((e) => (
            <div key={e.event} className="border-b border-border/60 pb-4 last:border-0 last:pb-0">
              <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium text-foreground">{e.event}</span>
                <div className="flex items-center gap-2">
                  <Badge tone={DIR_TONE[e.direction]}>{e.direction}</Badge>
                  <span className="text-xs text-muted-foreground">赔率 {e.odds}</span>
                </div>
              </div>
              <div className="mb-1.5 flex items-center gap-3">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn("h-full rounded-full", e.probability >= 50 ? "bg-danger" : "bg-success")}
                    style={{ width: `${e.probability}%` }}
                  />
                </div>
                <span className="w-10 text-right text-sm font-medium tabular-nums text-foreground">{e.probability}%</span>
              </div>
              <p className="text-xs text-muted-foreground">影响: {e.affected}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
