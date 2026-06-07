import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Pencil, Plus, RefreshCw, RotateCcw, Trash2, Bot, Loader2 } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { opportunitiesSeed, type Opportunity, type OppStatus } from "@/data/opportunitiesSeed";
import { useLiveQuotes } from "@/hooks/useLiveQuotes";
import { loadPersisted, savePersisted, clearPersisted } from "@/lib/persist";
import { changeColorClass, fmtPct, fmtPrice } from "@/lib/cn-market";
import { launchAgentFromPage } from "@/lib/agent-launch";
import { cn } from "@/lib/utils";

const STORE = "opportunities";
const STATUSES: OppStatus[] = ["关注", "待买", "已买"];
const STATUS_TONE: Record<OppStatus, "info" | "warning" | "success"> = {
  关注: "info",
  待买: "warning",
  已买: "success",
};

export function Opportunities() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<Opportunity[]>(() => loadPersisted(STORE, opportunitiesSeed));
  const [editing, setEditing] = useState(false);
  const [filter, setFilter] = useState("全部");
  const [researchingCode, setResearchingCode] = useState<string | null>(null);

  useEffect(() => savePersisted(STORE, rows), [rows]);

  const codes = useMemo(() => rows.map((r) => r.code), [rows]);
  const { quotes, stale, updatedAt, loading, refresh } = useLiveQuotes(codes);

  // Hand one candidate to the Vibe-Trading agent for a web-grounded research
  // brief, then open the Agent chat to watch it reason and call tools.
  const researchOne = async (o: Opportunity) => {
    setResearchingCode(o.code);
    try {
      const price = quotes[o.code]?.price ?? null;
      const upside = price && price > 0 ? ((o.target - price) / price) * 100 : null;
      const prompt =
        `请联网研究以下 A 股候选标的，给出研究纪要与买入论证。\n\n` +
        `标的：${o.name}(${o.code})\n板块：${o.sector}\n触发逻辑：${o.trigger}\n` +
        `现价：${price == null ? "未知" : fmtPrice(price)}　目标价：${fmtPrice(o.target)}` +
        `${upside == null ? "" : `（距目标 ${fmtPct(upside)}）`}　我的评分：${o.score}\n\n` +
        `要求：\n1. 用 web_search 检索最新基本面、产业进展、催化与风险；\n` +
        `2. 评估「触发逻辑」是否成立、目标价是否合理；\n` +
        `3. 给出买入论证、关键风险、合理买点/区间与需跟踪的指标；\n` +
        `4. 用中文，结构化输出（要点或表格）。`;
      await launchAgentFromPage(
        navigate,
        `研究·${o.name}`,
        prompt,
        "收到，正在检索基本面并评估机会逻辑…",
      );
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "无法启动 Agent 研究（需后端运行）");
    } finally {
      setResearchingCode(null);
    }
  };

  const sectors = useMemo(
    () => ["全部", ...Array.from(new Set(rows.map((o) => o.sector.split("·")[0])))],
    [rows],
  );
  const visible = filter === "全部" ? rows : rows.filter((o) => o.sector.startsWith(filter));

  const update = (i: number, patch: Partial<Opportunity>) =>
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  const addRow = () =>
    setRows((rs) => [...rs, { name: "新机会", code: "000000", sector: "其他", trigger: "", target: 0, score: 60, status: "关注" }]);
  const removeRow = (orig: Opportunity) => setRows((rs) => rs.filter((r) => r !== orig));
  const reset = () => {
    clearPersisted(STORE);
    setRows(opportunitiesSeed);
  };

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="机会清单"
        subtitle="候选标的与触发逻辑（现价实时刷新, 距目标价实时计算）"
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

      <div className="mb-4 flex flex-wrap gap-1.5">
        {sectors.map((s) => (
          <button key={s} onClick={() => setFilter(s)} className={cn("rounded-md border px-3 py-1 text-sm", filter === s ? "border-primary bg-primary/10 text-primary" : "bg-card text-muted-foreground hover:text-foreground")}>
            {s}
          </button>
        ))}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="px-3 py-2 text-left font-medium">标的</th>
                <th className="px-3 py-2 text-left font-medium">板块</th>
                <th className="px-3 py-2 text-left font-medium">触发逻辑</th>
                <th className="px-3 py-2 text-right font-medium">现价</th>
                <th className="px-3 py-2 text-right font-medium">目标价</th>
                <th className="px-3 py-2 text-right font-medium">距目标</th>
                <th className="px-3 py-2 text-right font-medium">评分</th>
                <th className="px-3 py-2 text-left font-medium">状态</th>
                <th className="px-3 py-2 text-right font-medium">{editing ? "" : "操作"}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((o) => {
                const i = rows.indexOf(o);
                const price = quotes[o.code]?.price ?? null;
                const upside = price && price > 0 ? ((o.target - price) / price) * 100 : null;
                return (
                  <tr key={i} className="border-b border-border/60 last:border-0">
                    <td className="px-3 py-2.5">
                      {editing ? (
                        <div className="flex gap-1">
                          <input value={o.name} onChange={(e) => update(i, { name: e.target.value })} className="w-24 rounded border bg-background px-1.5 py-1 text-xs" />
                          <input value={o.code} onChange={(e) => update(i, { code: e.target.value })} className="w-20 rounded border bg-background px-1.5 py-1 text-xs" />
                        </div>
                      ) : (
                        <span><span className="font-medium text-foreground">{o.name}</span> <span className="ml-1 text-xs text-muted-foreground">{o.code}</span></span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      {editing ? <input value={o.sector} onChange={(e) => update(i, { sector: e.target.value })} className="w-28 rounded border bg-background px-1.5 py-1 text-xs" /> : o.sector}
                    </td>
                    <td className="px-3 py-2.5">
                      {editing ? <input value={o.trigger} onChange={(e) => update(i, { trigger: e.target.value })} className="w-40 rounded border bg-background px-1.5 py-1 text-xs" /> : o.trigger}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">{price == null ? "—" : fmtPrice(price)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {editing ? <input type="number" value={o.target} onChange={(e) => update(i, { target: Number(e.target.value) })} className="w-20 rounded border bg-background px-1.5 py-1 text-right text-xs" /> : fmtPrice(o.target)}
                    </td>
                    <td className={cn("px-3 py-2.5 text-right tabular-nums", upside == null ? "text-muted-foreground" : changeColorClass(upside))}>
                      {upside == null ? "—" : fmtPct(upside)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {editing ? <input type="number" value={o.score} onChange={(e) => update(i, { score: Number(e.target.value) })} className="w-14 rounded border bg-background px-1.5 py-1 text-right text-xs" /> : <span className={cn("font-medium", o.score >= 85 ? "text-danger" : "text-foreground")}>{o.score}</span>}
                    </td>
                    <td className="px-3 py-2.5">
                      {editing ? (
                        <select value={o.status} onChange={(e) => update(i, { status: e.target.value as OppStatus })} className="rounded border bg-background px-1.5 py-1 text-xs">
                          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      ) : <Badge tone={STATUS_TONE[o.status]}>{o.status}</Badge>}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {editing ? (
                        <button onClick={() => removeRow(o)} className="text-muted-foreground hover:text-danger"><Trash2 className="h-4 w-4" /></button>
                      ) : (
                        <button
                          onClick={() => researchOne(o)}
                          disabled={researchingCode !== null}
                          className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50"
                          title="让 Agent 联网研究该标的"
                        >
                          {researchingCode === o.code ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Bot className="h-3.5 w-3.5" />}
                          研究
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {editing && (
          <div className="mt-3 flex gap-2">
            <button onClick={addRow} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><Plus className="h-3 w-3" /> 添加机会</button>
            <button onClick={reset} className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"><RotateCcw className="h-3 w-3" /> 重置为示例</button>
          </div>
        )}
      </Card>

      <p className="mt-4 text-xs text-muted-foreground">
        现价更新: {updatedAt || "—"}
        {stale && <span className="ml-1 text-warning">（行情源暂不可用, 现价/距目标暂不可得）</span>}
      </p>
    </div>
  );
}
