import { useStockChartDrawer } from "@/contexts/StockChartDrawerContext";
import { cn } from "@/lib/utils";

export function StockSymbolButton({
  code,
  name,
  className,
  layout = "stacked",
}: {
  code: string;
  name: string;
  className?: string;
  /** stacked: name + code; inline: name (code) on one line */
  layout?: "stacked" | "inline";
}) {
  const { open } = useStockChartDrawer();

  return (
    <button
      type="button"
      onClick={() => open({ code, name })}
      className={cn(
        "rounded-sm text-left transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        className,
      )}
      title="查看 K 线"
    >
      {layout === "inline" ? (
        <span>
          <span className="font-medium">{name}</span>
          <span className="ml-1 text-xs text-muted-foreground">({code})</span>
        </span>
      ) : (
        <>
          <span className="font-medium text-foreground">{name}</span>
          <span className="ml-1.5 text-xs text-muted-foreground">{code}</span>
        </>
      )}
    </button>
  );
}

/** Clickable code only (valuation table code column). */
export function StockCodeButton({
  code,
  name,
  className,
}: {
  code: string;
  name: string;
  className?: string;
}) {
  const { open } = useStockChartDrawer();

  return (
    <button
      type="button"
      onClick={() => open({ code, name })}
      className={cn(
        "rounded-sm text-muted-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        className,
      )}
      title="查看 K 线"
    >
      {code}
    </button>
  );
}
