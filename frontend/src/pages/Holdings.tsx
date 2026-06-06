import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, RefreshCw, RotateCcw, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { holdingsSeed, type DecisionAction, type Holding } from "@/data/holdingsSeed";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { loadPersisted, savePersisted, clearPersisted } from "@/lib/persist";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { cn } from "@/lib/utils";

const STORE = "holdings";
const ACTIONS: DecisionAction[] = ["加仓", "减仓", "持有", "清仓"];
const ACTION_TONE: Record<DecisionAction, "danger" | "success" | "neutral" | "warning"> = {
  加仓: "danger",
  减仓: "success",
  持有: "neutral",
  清仓: "warning",
};

export function Holdings() {
  const [rows, setRows] = useState<Holding[]>(() => loadPersisted(STORE, holdingsSeed));
  const [editing, setEditing] = useState(false);

  useEffect(() => savePersisted(STORE, rows), [rows]);

  const codes = useMemo(() => rows.map((r) => r.code), [rows]);
  const { quotes, stale, updatedAt, loading, refresh } = useLiveQuotes(codes);

  const priceOf = (h: Holding) => quotes[h.code]?.price ?? h.price;
  const update = (i: number, patch: Partial<Holding>) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  const addRow = () =>
    setRows((rs) => [...rs, { name: "新标的", code: "000000", cost: 0, price: 0, position: 0, action: "持有", reason: "" }]);
  const removeRow = (i: number) => setRows((rs) => rs.filter((_, idx) => idx !== i));
  const reset = () => {
    clearPersisted(STORE);
    setRows(holdingsSeed);
  };

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="持仓决策"
        subtitle="当前持仓与加/减/持决策建议（现价实时刷新, 盈亏实时计算）"
        actions={
          <div className="flex items-center gap-2">
            <button onClick={refresh} className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground">
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} /> 刷新
            </button>
            <button onClick={() => setEditing((e) => !e)} className={cn("inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm", editing ? "border-primary bg-primary/10 text-primary" : "bg-card text-muted-foreground hover:text-foreground")}>
              <Pencil className="h-4 w-4" /> {editing ? "完成" : "编辑"}
            </button>
          </div>
        }
      />

      <Card className="mb-4">
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
                {editing && <th className="px-3 py-2" />}
              </tr>
            </thead>
            <tbody>
              {rows.map((h, i) => {
                const price = priceOf(h);
                const pnl = h.cost ? ((price - h.cost) / h.cost) * 100 : 0;
                return (
                  <tr key={i} className="border-b border-border/60 last:border-0">
                    <td className="px-3 py-2.5">
                      {editing ? (
                        <div className="flex gap-1">
                          <input value={h.name} onChange={(e) => update(i, { name: e.target.value })} className="w-24 rounded border bg-background px-1.5 py-1 text-xs" />
                          <input value={h.code} onChange={(e) => update(i, { code: e.target.value })} className="w-20 rounded border bg-background px-1.5 py-1 text-xs" />
                        </div>
                      ) : (
                        <span><span className="font-medium text-foreground">{h.name}</span> <span className="ml-1 text-xs text-muted-foreground">{h.code}</span></span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {editing ? (
                        <input type="number" value={h.cost} onChange={(e) => update(i, { cost: Number(e.target.value) })} className="w-20 rounded border bg-background px-1.5 py-1 text-right text-xs" />
                      ) : fmtPrice(h.cost)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{fmtPrice(price)}</td>
                    <td className={cn("px-3 py-2.5 text-right font-medium tabular-nums", changeColorClass(pnl))}>{fmtPct(pnl)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {editing ? (
                        <input type="number" value={h.position} onChange={(e) => update(i, { position: Number(e.target.value) })} className="w-16 rounded border bg-background px-1.5 py-1 text-right text-xs" />
                      ) : `${h.position}%`}
                    </td>
                    <td className="px-3 py-2.5">
                      {editing ? (
                        <select value={h.action} onChange={(e) => update(i, { action: e.target.value as DecisionAction })} className="rounded border bg-background px-1.5 py-1 text-xs">
                          {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
                        </select>
                      ) : <Badge tone={ACTION_TONE[h.action]}>{h.action}</Badge>}
                    </td>
                    {editing && (
                      <td className="px-3 py-2.5 text-right">
                        <button onClick={() => removeRow(i)} className="text-muted-foreground hover:text-danger"><Trash2 className="h-4 w-4" /></button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {editing && (
          <div className="mt-3 flex gap-2">
            <button onClick={addRow} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><Plus className="h-3 w-3" /> 添加持仓</button>
            <button onClick={reset} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><RotateCcw className="h-3 w-3" /> 重置为示例</button>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {rows.map((h, i) => (
          <Card key={i} title={<span>{h.name} <span className="text-xs text-muted-foreground">{h.code}</span></span>}>
            <div className="mb-2"><Badge tone={ACTION_TONE[h.action]}>{h.action}</Badge></div>
            {editing ? (
              <textarea value={h.reason} onChange={(e) => update(i, { reason: e.target.value })} rows={3} className="w-full rounded border bg-background px-2 py-1 text-sm" />
            ) : (
              <p className="text-sm leading-relaxed text-muted-foreground">{h.reason}</p>
            )}
          </Card>
        ))}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        现价更新: {updatedAt || "—"}
        {stale && <span className="ml-1 text-warning">（行情源暂不可用, 现价显示示例数据）</span>}
      </p>
    </div>
  );
}
