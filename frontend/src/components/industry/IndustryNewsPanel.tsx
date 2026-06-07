import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Badge } from "@/components/dashboard/Badge";
import { newsSeed } from "@/data/newsSeed";
import { api, type NewsItemWire } from "@/lib/api";
import { cn } from "@/lib/utils";

export function IndustryNewsPanel({
  keywords,
  subtitle = "产业链相关资讯（新浪财经）",
}: {
  keywords: string[];
  subtitle?: string;
}) {
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
    void refresh();
  }, [refresh]);

  const filtered = rows.filter((n) => {
    const blob = `${n.title} ${n.summary}`;
    return keywords.some((k) => blob.includes(k)) || n.tickers.some((t) => keywords.some((k) => t.includes(k)));
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">{subtitle}</p>
        <button
          type="button"
          onClick={() => void refresh()}
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
