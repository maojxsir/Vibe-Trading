import { RefreshCw, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function ModuleStockActions({
  onRefreshQuotes,
  quotesLoading,
  onAgentRefresh,
  agentLoading,
  onReset,
  refreshedAt,
  genError,
}: {
  onRefreshQuotes: () => void;
  quotesLoading: boolean;
  onAgentRefresh: () => void;
  agentLoading: boolean;
  onReset: () => void;
  refreshedAt?: string;
  genError: string | null;
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onAgentRefresh}
          disabled={agentLoading}
          className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5 text-sm text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
        >
          <Sparkles className={cn("h-4 w-4", agentLoading && "animate-pulse")} />
          {agentLoading ? "Agent 生成中…" : "Agent 刷新标的"}
        </button>
        <button
          type="button"
          onClick={onRefreshQuotes}
          disabled={quotesLoading}
          className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <RefreshCw className={cn("h-4 w-4", quotesLoading && "animate-spin")} />
          刷新行情
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={agentLoading}
          className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          恢复默认
        </button>
        {refreshedAt && (
          <span className="text-xs text-muted-foreground">
            Agent 更新：{new Date(refreshedAt).toLocaleString()}
          </span>
        )}
      </div>
      {genError && <p className="text-xs text-danger">{genError}</p>}
    </div>
  );
}
