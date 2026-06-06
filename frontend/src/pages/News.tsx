import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { newsSeed } from "@/data/newsSeed";
import { api, type NewsItemWire } from "@/lib/api";
import { cn } from "@/lib/utils";

const REFRESH_MS = 60_000;

type NewsRow = NewsItemWire;

const seedRows: NewsRow[] = newsSeed.map((n) => ({ ...n, url: "" }));

export function News() {
  const [rows, setRows] = useState<NewsRow[]>(seedRows);
  const [stale, setStale] = useState(true);
  const [updatedAt, setUpdatedAt] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const wire = await api.getNews();
      if (wire.stale || wire.items.length === 0) {
        setStale(true);
      } else {
        setRows(wire.items);
        setStale(false);
        setUpdatedAt(wire.updatedAt);
      }
    } catch {
      setStale(true);
    } finally {
      setLoading(false);
    }
  }, []);

  const timer = useRef<number | null>(null);
  useEffect(() => {
    refresh();
    timer.current = window.setInterval(refresh, REFRESH_MS);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [refresh]);

  const items = [...rows].sort((a, b) => b.time.localeCompare(a.time));

  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageHeader
        title="新闻"
        subtitle="财经资讯流（实时抓取, 按时间倒序）"
        actions={
          <button onClick={refresh} className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground">
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} /> 刷新
          </button>
        }
      />

      <div className="space-y-3">
        {items.map((n, i) => (
          <Card key={i}>
            <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
              <span className="font-medium text-primary">{n.source}</span>
              <span>·</span>
              <span>{n.time}</span>
            </div>
            {n.url ? (
              <a href={n.url} target="_blank" rel="noopener noreferrer" className="mb-1 block font-semibold text-foreground hover:text-primary">
                {n.title}
              </a>
            ) : (
              <h3 className="mb-1 font-semibold text-foreground">{n.title}</h3>
            )}
            {n.summary && <p className="mb-2 text-sm leading-relaxed text-muted-foreground">{n.summary}</p>}
            {n.tickers.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {n.tickers.map((t) => (
                  <Badge key={t} tone="info">{t}</Badge>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        更新: {updatedAt || "—"}
        {stale && <span className="ml-1 text-warning">（新闻源暂不可用, 显示缓存示例）</span>}
      </p>
    </div>
  );
}
