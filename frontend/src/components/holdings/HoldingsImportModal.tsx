import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";
import { Badge } from "@/components/dashboard/Badge";
import type { HoldingImportRowWire } from "@/lib/api";
import { cn } from "@/lib/utils";

interface HoldingsImportModalProps {
  open: boolean;
  rows: HoldingImportRowWire[];
  existingCodes: string[];
  onCancel: () => void;
  onConfirm: (rows: HoldingImportRowWire[]) => void;
}

export function HoldingsImportModal({ open, rows, existingCodes, onCancel, onConfirm }: HoldingsImportModalProps) {
  const [draft, setDraft] = useState<HoldingImportRowWire[]>([]);
  const [checked, setChecked] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) return;
    setDraft(rows.map((row) => ({ ...row })));
    setChecked(new Set(rows.map((row) => row.code)));
  }, [open, rows]);

  const existing = useMemo(() => new Set(existingCodes), [existingCodes]);
  const selectedRows = draft.filter((row) => checked.has(row.code));
  const updateCount = selectedRows.filter((row) => existing.has(row.code) || row.action === "update").length;
  const appendCount = selectedRows.length - updateCount;
  const keepCount = existingCodes.filter((code) => !draft.some((row) => row.code === code)).length;

  const patch = (code: string, patchRow: Partial<HoldingImportRowWire>) => {
    setDraft((current) => current.map((row) => (row.code === code ? { ...row, ...patchRow } : row)));
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[86vh] w-full max-w-5xl flex-col rounded-lg border bg-card shadow-xl">
        <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">截图导入预览</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              将更新 {updateCount} 只，新增 {appendCount} 只；{keepCount} 只现有持仓不在截图中，将保留
            </p>
          </div>
          <button type="button" onClick={onCancel} className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="overflow-auto p-4">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="px-2 py-2 text-left font-medium">导入</th>
                <th className="px-2 py-2 text-left font-medium">名称</th>
                <th className="px-2 py-2 text-left font-medium">代码</th>
                <th className="px-2 py-2 text-right font-medium">成本</th>
                <th className="px-2 py-2 text-right font-medium">持仓(股)</th>
                <th className="px-2 py-2 text-right font-medium">仓位%</th>
                <th className="px-2 py-2 text-left font-medium">操作</th>
                <th className="px-2 py-2 text-left font-medium">置信度</th>
              </tr>
            </thead>
            <tbody>
              {draft.map((row) => {
                const lowConfidence = row.confidence < 0.7;
                const isUpdate = existing.has(row.code) || row.action === "update";
                return (
                  <tr key={row.code} className={cn("border-b border-border/60 last:border-0", lowConfidence && "bg-warning/5")}>
                    <td className="px-2 py-2.5">
                      <input
                        type="checkbox"
                        checked={checked.has(row.code)}
                        onChange={(event) => {
                          setChecked((current) => {
                            const next = new Set(current);
                            if (event.target.checked) next.add(row.code);
                            else next.delete(row.code);
                            return next;
                          });
                        }}
                      />
                    </td>
                    <td className="px-2 py-2.5 font-medium text-foreground">{row.name}</td>
                    <td className="px-2 py-2.5 font-mono text-xs text-muted-foreground">{row.code}</td>
                    <td className="px-2 py-2.5 text-right">
                      <input
                        type="number"
                        value={row.cost ?? ""}
                        onChange={(event) => patch(row.code, { cost: Number(event.target.value) })}
                        className="w-24 rounded border bg-background px-2 py-1 text-right text-xs"
                      />
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <input
                        type="number"
                        value={row.shares ?? ""}
                        onChange={(event) =>
                          patch(row.code, { shares: event.target.value === "" ? null : Number(event.target.value) })
                        }
                        className="w-24 rounded border bg-background px-2 py-1 text-right text-xs"
                      />
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <input
                        type="number"
                        value={row.position ?? ""}
                        onChange={(event) =>
                          patch(row.code, { position: event.target.value === "" ? null : Number(event.target.value) })
                        }
                        className="w-20 rounded border bg-background px-2 py-1 text-right text-xs"
                      />
                    </td>
                    <td className="px-2 py-2.5">
                      <Badge tone={isUpdate ? "primary" : "success"}>{isUpdate ? "更新" : "新增"}</Badge>
                    </td>
                    <td className="px-2 py-2.5">
                      <div className={cn("inline-flex items-center gap-1", lowConfidence ? "text-warning" : "text-success")}>
                        {lowConfidence ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                        <span className="tabular-nums">{Math.round(row.confidence * 100)}%</span>
                      </div>
                      {row.warnings?.length ? (
                        <span className="ml-2 text-[11px] text-muted-foreground">{row.warnings.join(", ")}</span>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <footer className="flex items-center justify-end gap-2 border-t px-4 py-3">
          <button type="button" onClick={onCancel} className="rounded-md border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground">
            取消
          </button>
          <button
            type="button"
            onClick={() => onConfirm(selectedRows)}
            disabled={selectedRows.length === 0}
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
          >
            确认导入
          </button>
        </footer>
      </div>
    </div>
  );
}
