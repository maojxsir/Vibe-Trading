import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { holdingsSeed, type DecisionAction } from "@/data/holdingsSeed";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

const ACTION_TONE: Record<DecisionAction, "danger" | "success" | "neutral" | "warning"> = {
  加仓: "danger",
  减仓: "success",
  持有: "neutral",
  清仓: "warning",
};

function pnlPct(cost: number, price: number): number {
  return ((price - cost) / cost) * 100;
}

export function Holdings() {
  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader title="持仓决策" subtitle="当前持仓与对应的加/减/持决策建议" />

      <Card title="当前持仓" className="mb-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="px-3 py-2 text-left font-medium">标的</th>
                <th className="px-3 py-2 text-right font-medium">成本</th>
                <th className="px-3 py-2 text-right font-medium">现价</th>
                <th className="px-3 py-2 text-right font-medium">盈亏</th>
                <th className="px-3 py-2 text-right font-medium">仓位</th>
                <th className="px-3 py-2 text-left font-medium">决策</th>
              </tr>
            </thead>
            <tbody>
              {holdingsSeed.map((h) => {
                const pnl = pnlPct(h.cost, h.price);
                return (
                  <tr key={h.code} className="border-b border-border/60 last:border-0">
                    <td className="px-3 py-2.5">
                      <span className="font-medium text-foreground">{h.name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{h.code}</span>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtPrice(h.cost)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtPrice(h.price)}</td>
                    <td className={cn("px-3 py-2.5 text-right font-medium tabular-nums", changeColorClass(pnl))}>{fmtPct(pnl)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{h.position}%</td>
                    <td className="px-3 py-2.5"><Badge tone={ACTION_TONE[h.action]}>{h.action}</Badge></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {holdingsSeed.map((h) => (
          <Card key={h.code} title={<span>{h.name} <span className="text-xs text-muted-foreground">{h.code}</span></span>}>
            <div className="mb-2"><Badge tone={ACTION_TONE[h.action]}>{h.action}</Badge></div>
            <p className="text-sm leading-relaxed text-muted-foreground">{h.reason}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
