import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Pencil, Plus, RefreshCw, RotateCcw, Trash2, Bot, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { eventsSeed, type EventDir, type MarketEvent } from "@/data/eventsSeed";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { loadPersisted, savePersisted, clearPersisted } from "@/lib/persist";
import { changeColorClass, fmtPct } from "@/lib/cn-market";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const STORE = "events";
const DIRS: EventDir[] = ["利好", "利空", "中性"];
const DIR_TONE: Record<EventDir, "danger" | "success" | "neutral"> = {
  利好: "danger",
  利空: "success",
  中性: "neutral",
};

export function Events() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<MarketEvent[]>(() => loadPersisted(STORE, eventsSeed));
  const [editing, setEditing] = useState(false);
  const [evalIdx, setEvalIdx] = useState<number | null>(null);

  useEffect(() => savePersisted(STORE, rows), [rows]);

  const codes = useMemo(() => Array.from(new Set(rows.flatMap((e) => e.tickers.map((t) => t.code)))), [rows]);
  const { quotes, stale, updatedAt, loading, refresh } = useLiveQuotes(codes);

  // Hand one event to the Vibe-Trading agent for a web-grounded probability /
  // transmission-path assessment, then open the Agent chat.
  const evaluateEvent = async (e: MarketEvent, idx: number) => {
    setEvalIdx(idx);
    try {
      const tickers = e.tickers.map((t) => `${t.name}(${t.code})`).join("、") || "（宏观/无单一标的）";
      const prompt =
        `请联网评估以下市场事件的发生概率与传导路径。\n\n` +
        `事件：${e.event}\n方向（我的判断）：${e.direction}\n我的概率估计：${e.probability}%\n影响标的：${tickers}\n\n` +
        `要求：\n1. 用 web_search 检索最新进展与依据；\n` +
        `2. 给出你对发生概率的独立判断（给区间）与关键假设；\n` +
        `3. 梳理传导路径：触发因素→传导逻辑→受益/受损板块→具体标的；\n` +
        `4. 指出方向（利好/利空）、弹性大小与需跟踪的信号；\n` +
        `5. 用中文，结构化输出。`;
      const session = await api.createSession(`事件评估·${e.event}`.slice(0, 40));
      await api.sendMessage(session.session_id, prompt);
      navigate(`/agent?session=${session.session_id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "无法启动 Agent 评估（需后端运行）");
      setEvalIdx(null);
    }
  };

  const update = (i: number, patch: Partial<MarketEvent>) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  const addRow = () =>
    setRows((rs) => [...rs, { event: "新事件", probability: 50, affected: "", tickers: [], direction: "中性", odds: "中" }]);
  const removeRow = (i: number) => setRows((rs) => rs.filter((_, idx) => idx !== i));
  const reset = () => {
    clearPersisted(STORE);
    setRows(eventsSeed);
  };

  return (
    <div className="mx-auto max-w-5xl p-6">
      <PageHeader
        title="事件概率"
        subtitle="关键事件的发生概率（人工维护）与影响标的的实时行情"
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

      <Card>
        <div className="space-y-4">
          {rows.map((e, i) => (
            <div key={i} className="border-b border-border/60 pb-4 last:border-0 last:pb-0">
              <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                {editing ? (
                  <input value={e.event} onChange={(ev) => update(i, { event: ev.target.value })} className="flex-1 rounded border bg-background px-2 py-1 text-sm" />
                ) : (
                  <span className="font-medium text-foreground">{e.event}</span>
                )}
                <div className="flex items-center gap-2">
                  {editing ? (
                    <select value={e.direction} onChange={(ev) => update(i, { direction: ev.target.value as EventDir })} className="rounded border bg-background px-1.5 py-1 text-xs">
                      {DIRS.map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  ) : <Badge tone={DIR_TONE[e.direction]}>{e.direction}</Badge>}
                  <span className="text-xs text-muted-foreground">赔率 {e.odds}</span>
                  {!editing && (
                    <button
                      onClick={() => evaluateEvent(e, i)}
                      disabled={evalIdx !== null}
                      className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50"
                      title="让 Agent 联网评估该事件"
                    >
                      {evalIdx === i ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bot className="h-3.5 w-3.5" />}
                      评估
                    </button>
                  )}
                  {editing && <button onClick={() => removeRow(i)} className="text-muted-foreground hover:text-danger"><Trash2 className="h-4 w-4" /></button>}
                </div>
              </div>

              <div className="mb-1.5 flex items-center gap-3">
                {editing ? (
                  <input type="range" min={0} max={100} value={e.probability} onChange={(ev) => update(i, { probability: Number(ev.target.value) })} className="flex-1 accent-primary" />
                ) : (
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className={cn("h-full rounded-full", e.probability >= 50 ? "bg-danger" : "bg-success")} style={{ width: `${e.probability}%` }} />
                  </div>
                )}
                <span className="w-10 text-right text-sm font-medium tabular-nums text-foreground">{e.probability}%</span>
              </div>

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span>影响: {e.affected || "—"}</span>
                {e.tickers.map((t) => {
                  const q = quotes[t.code];
                  return (
                    <span key={t.code} className="inline-flex items-center gap-1">
                      {t.name}
                      {q ? <span className={cn("tabular-nums", changeColorClass(q.changePct))}>{fmtPct(q.changePct)}</span> : <span className="text-muted-foreground/60">—</span>}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        {editing && (
          <div className="mt-3 flex gap-2">
            <button onClick={addRow} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><Plus className="h-3 w-3" /> 添加事件</button>
            <button onClick={reset} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><RotateCcw className="h-3 w-3" /> 重置为示例</button>
          </div>
        )}
      </Card>

      <p className="mt-4 text-xs text-muted-foreground">
        影响标的行情更新: {updatedAt || "—"}
        {stale && <span className="ml-1 text-warning">（行情源暂不可用）</span>}
      </p>
    </div>
  );
}
