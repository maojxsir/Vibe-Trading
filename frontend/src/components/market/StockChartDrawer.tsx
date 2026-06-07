import { useEffect } from "react";
import { Loader2, X } from "lucide-react";
import { CandlestickChart } from "@/components/charts/CandlestickChart";
import type { StockChartTarget } from "@/contexts/StockChartDrawerContext";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { useStockKline } from "@/hooks/useStockKline";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

export function StockChartDrawer({
  target,
  onClose,
}: {
  target: StockChartTarget | null;
  onClose: () => void;
}) {
  const open = target != null;
  const code = target?.code ?? null;
  const { bars, loading, error, source } = useStockKline(open ? code : null);
  const { quotes } = useLiveQuotes(code ? [code] : []);
  const quote = code ? quotes[code] : undefined;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !target) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="关闭"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <aside
        className={cn(
          "relative flex h-full w-full max-w-[560px] flex-col border-l bg-card shadow-xl",
          "animate-in slide-in-from-right duration-200",
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b px-4 py-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-foreground">
              {target.name}
              <span className="ml-2 text-sm font-normal text-muted-foreground">{target.code}</span>
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
              {quote?.price != null ? (
                <>
                  <span className="font-medium tabular-nums">{fmtPrice(quote.price)}</span>
                  <span className={cn("tabular-nums", changeColorClass(quote.changePct))}>
                    {fmtPct(quote.changePct)}
                  </span>
                </>
              ) : (
                <span className="text-muted-foreground">现价加载中…</span>
              )}
              {source && !loading && bars.length > 0 && (
                <span className="text-xs text-muted-foreground">数据源 {source}</span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {loading && bars.length === 0 ? (
            <div className="flex h-[420px] items-center justify-center text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              加载 K 线…
            </div>
          ) : error && bars.length === 0 ? (
            <div className="flex h-[420px] items-center justify-center px-4 text-center text-sm text-muted-foreground">
              {error}
            </div>
          ) : (
            <div className="relative">
              {loading && (
                <div className="absolute right-2 top-2 z-10 rounded bg-card/90 px-2 py-1 text-xs text-muted-foreground">
                  <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
                  更新中
                </div>
              )}
              <CandlestickChart data={bars} height={420} />
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
