import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { newsSeed } from "@/data/newsSeed";

export function News() {
  const items = [...newsSeed].sort((a, b) => b.time.localeCompare(a.time));

  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageHeader title="新闻" subtitle="产业链相关资讯流（按时间倒序）" />

      <div className="space-y-3">
        {items.map((n, i) => (
          <Card key={i}>
            <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium text-primary">{n.source}</span>
              <span>·</span>
              <span>{n.time}</span>
            </div>
            <h3 className="mb-1 font-semibold text-foreground">{n.title}</h3>
            <p className="mb-2 text-sm leading-relaxed text-muted-foreground">{n.summary}</p>
            <div className="flex flex-wrap gap-1.5">
              {n.tickers.map((t) => (
                <Badge key={t} tone="info">{t}</Badge>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
