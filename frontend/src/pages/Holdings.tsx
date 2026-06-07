import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Pencil, Plus, RefreshCw, RotateCcw, Trash2, Bot, Loader2, FileUp } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { StockSymbolCombobox } from "@/components/dashboard/StockSymbolCombobox";
import { HoldingsImportModal } from "@/components/holdings/HoldingsImportModal";
import { holdingsSeed, type DecisionAction, type Holding } from "@/data/holdingsSeed";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { loadPersisted, savePersisted, clearPersisted } from "@/lib/persist";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { api, type HoldingImportRowWire } from "@/lib/api";
import { mergeHoldings } from "@/lib/holdings-merge";
import { loadRecent, pushRecent } from "@/lib/recent-symbols";
import { cn } from "@/lib/utils";

const STORE = "holdings";
const ACTIONS: DecisionAction[] = ["加仓", "减仓", "持有", "清仓"];
const ACTION_TONE: Record<DecisionAction, "danger" | "success" | "neutral" | "warning"> = {
  加仓: "danger",
  减仓: "success",
  持有: "neutral",
  清仓: "warning",
};
const SEED_BOOST_CODES = ["688017", "002472", "601689", "002050", "300124", "003021", "300308", "002463", "300476", "300394"];

export function Holdings() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Holding[]>(() => loadPersisted(STORE, holdingsSeed));
  const [editing, setEditing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importRows, setImportRows] = useState<HoldingImportRowWire[]>([]);
  const [importOpen, setImportOpen] = useState(false);
  const [recentCodes, setRecentCodes] = useState<string[]>(() => loadRecent());
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => savePersisted(STORE, rows), [rows]);

  const codes = useMemo(() => rows.map((r) => r.code), [rows]);
  const boostCodes = useMemo(
    () => Array.from(new Set([...recentCodes, ...rows.map((r) => r.code), ...SEED_BOOST_CODES])),
    [recentCodes, rows],
  );
  const { quotes, stale, updatedAt, loading, refresh } = useLiveQuotes(codes);

  const priceOf = (h: Holding) => quotes[h.code]?.price ?? h.price;

  // Hand the live holdings to the Vibe-Trading agent for a review, then open the
  // Agent chat (with SSE replay) to watch it reason and call tools.
  const reviewWithAgent = async () => {
    setReviewing(true);
    try {
      const lines = rows
        .map((h, i) => {
          const price = priceOf(h);
          const pnl = h.cost ? ((price - h.cost) / h.cost) * 100 : 0;
          return `${i + 1}. ${h.name}(${h.code}) 成本${fmtPrice(h.cost)} 现价${fmtPrice(price)} 盈亏${fmtPct(pnl)} 仓位${h.position}% 当前决策:${h.action} 理由:${h.reason || "—"}`;
        })
        .join("\n");
      const prompt =
        `请帮我复盘以下 A 股持仓组合，并给出加/减/持建议。\n\n持仓明细：\n${lines}\n\n` +
        `要求：\n1. 逐一评估每只标的的盈亏、估值水平与投资逻辑是否仍然成立；\n` +
        `2. 指出主要风险点与组合集中度问题；\n` +
        `3. 如有需要可调用回测、行情或检索工具佐证；\n` +
        `4. 最后给出每只标的明确的加/减/持建议，以及组合层面的调整建议。\n` +
        `请用中文，分标的、用要点或表格输出。`;
      const session = await api.createSession("持仓复盘");
      await api.sendMessage(session.session_id, prompt);
      navigate(`/agent?session=${session.session_id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "无法启动 Agent 复盘（需后端运行）");
      setReviewing(false);
    }
  };
  const update = (i: number, patch: Partial<Holding>) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  const addRow = () =>
    setRows((rs) => [...rs, { name: "新标的", code: "000000", cost: 0, price: 0, position: 0, action: "持有", reason: "" }]);
  const removeRow = (i: number) => setRows((rs) => rs.filter((_, idx) => idx !== i));
  const reset = () => {
    clearPersisted(STORE);
    setRows(holdingsSeed);
  };

  const handleImportFile = useCallback(
    async (file: File) => {
      setImporting(true);
      try {
        const wire = await api.parseHoldingsScreenshot(file, rows.map((row) => row.code));
        setImportRows(wire.rows);
        setImportOpen(true);
        if (wire.meta.warnings?.length) {
          toast.warning(`导入提示: ${wire.meta.warnings.join(", ")}`);
        }
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "截图解析失败");
      } finally {
        setImporting(false);
      }
    },
    [rows],
  );

  useEffect(() => {
    if (!editing) return;
    const onPaste = (event: ClipboardEvent) => {
      const file = Array.from(event.clipboardData?.items ?? [])
        .find((item) => item.type.startsWith("image/"))
        ?.getAsFile();
      if (file) {
        event.preventDefault();
        void handleImportFile(file);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [editing, handleImportFile]);

  const confirmImport = (selected: HoldingImportRowWire[]) => {
    setRows((current) => mergeHoldings(current, selected));
    selected.forEach((row) => pushRecent(row.code));
    setRecentCodes(loadRecent());
    setImportOpen(false);
    setImportRows([]);
    toast.success(`已导入 ${selected.length} 条持仓`);
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
            {editing && (
              <>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={importing}
                  className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-60"
                >
                  {importing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
                  从截图导入
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.currentTarget.files?.[0];
                    event.currentTarget.value = "";
                    if (file) void handleImportFile(file);
                  }}
                />
              </>
            )}
            <button onClick={reviewWithAgent} disabled={reviewing} className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60">
              {reviewing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
              {reviewing ? "启动中…" : "用 Agent 复盘"}
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
                        <StockSymbolCombobox
                          value={{ name: h.name, code: h.code }}
                          boostCodes={boostCodes}
                          onSelect={(symbol) => {
                            update(i, { name: symbol.name, code: symbol.code });
                            pushRecent(symbol.code);
                            setRecentCodes(loadRecent());
                          }}
                        />
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
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button onClick={addRow} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><Plus className="h-3 w-3" /> 添加持仓</button>
            <button onClick={reset} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><RotateCcw className="h-3 w-3" /> 重置为示例</button>
            <span className="text-xs text-muted-foreground">截图可能包含账户信息；仅发送到本地后端解析，不会保存图片。</span>
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

      <HoldingsImportModal
        open={importOpen}
        rows={importRows}
        existingCodes={rows.map((row) => row.code)}
        onCancel={() => setImportOpen(false)}
        onConfirm={confirmImport}
      />
    </div>
  );
}
