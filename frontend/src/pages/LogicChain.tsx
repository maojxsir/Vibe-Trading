import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  Handle,
  Position,
  type Connection,
  type NodeProps,
  type NodeTypes,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Plus, Trash2, Sparkles, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { changeColorClass, fmtPct } from "@/lib/cn-market";
import { api, ApiError, type LogicChainNodeWire } from "@/lib/api";
import { clearPersisted, loadPersisted, savePersisted } from "@/lib/persist";
import {
  CHAIN_PRESETS,
  DEFAULT_CHAIN,
  KIND_LABEL,
  KIND_CLASS,
  KIND_DOT,
  loadChainGraph,
  type ChainKind,
  type ChainNode as ChainNodeT,
} from "@/data/logicChainSeed";

const STORAGE_PREFIX = "vt-logic-chain:";
const PRESETS_STORAGE_KEY = "logic-chain:presets:v2";
const KINDS: ChainKind[] = ["trigger", "transmit", "sector", "target"];
const COLUMN_X: Record<ChainKind, number> = { trigger: 0, transmit: 340, sector: 680, target: 1020 };

function formatAgentError(error: unknown, action: string): string {
  if (error instanceof ApiError) {
    if (error.status === 405 || /method not allowed/i.test(error.message)) {
      return `${action}失败：后端接口未加载（HTTP 405）。请重启 vibe-trading serve 后再试。`;
    }
    if (error.status === 404) {
      return `${action}失败：接口不存在（HTTP 404）。请重启后端到最新代码。`;
    }
    return `${action}失败：${error.message}`;
  }
  const detail = error instanceof Error ? error.message : "未知错误";
  return `${action}失败：${detail}（需后端运行且已配置 LLM key）`;
}

function loadChain(chain: string): { nodes: ChainNodeT[]; edges: Edge[] } {
  return loadChainGraph(chain);
}

// Convert an agent-generated chain into laid-out React Flow nodes/edges,
// stacking each kind in its own column.
function layoutGenerated(wireNodes: LogicChainNodeWire[], wireEdges: { source: string; target: string }[]): {
  nodes: ChainNodeT[];
  edges: Edge[];
} {
  const perCol: Record<ChainKind, number> = { trigger: 0, transmit: 0, sector: 0, target: 0 };
  const nodes: ChainNodeT[] = wireNodes.map((n) => {
    const y = 40 + perCol[n.kind] * 150;
    perCol[n.kind] += 1;
    return {
      id: n.id,
      type: "chainNode",
      position: { x: COLUMN_X[n.kind], y },
      data: { kind: n.kind, label: n.label, desc: n.desc, ...(n.code ? { code: n.code } : {}) },
    };
  });
  const edges: Edge[] = wireEdges.map((e, i) => ({ id: `e${i}-${e.source}-${e.target}`, source: e.source, target: e.target }));
  return { nodes, edges };
}

function ChainNodeComp({ id, data, selected }: NodeProps<ChainNodeT>) {
  const { setNodes } = useReactFlow();
  const [editing, setEditing] = useState(false);

  return (
    <div className={cn("w-52 rounded-lg border-2 p-2 shadow-sm", KIND_CLASS[data.kind], selected && "ring-2 ring-primary")}>
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-foreground/40" />
      <div className="mb-1 flex items-center justify-between gap-1">
        <span className="flex items-center gap-1">
          <span className={cn("h-2 w-2 rounded-full", KIND_DOT[data.kind])} />
          <span className="text-[10px] text-muted-foreground">{KIND_LABEL[data.kind]}</span>
        </span>
        {data.kind === "target" && data.changePct !== undefined && (
          <span className={cn("text-[10px] font-medium tabular-nums", changeColorClass(data.changePct))}>{fmtPct(data.changePct)}</span>
        )}
      </div>
      {editing ? (
        <input
          autoFocus
          defaultValue={data.label}
          onBlur={(e) => {
            const label = e.target.value;
            setNodes((nds) => nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, label } } : n)));
            setEditing(false);
          }}
          className="w-full rounded border bg-background px-1 py-0.5 text-xs outline-none"
        />
      ) : (
        <div className="text-xs font-semibold text-foreground" onDoubleClick={() => setEditing(true)}>
          {data.label}
          {data.code ? <span className="ml-1 font-normal text-muted-foreground">{data.code}</span> : null}
        </div>
      )}
      <div className="mt-1 text-[11px] leading-snug text-muted-foreground">{data.desc}</div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-foreground/40" />
    </div>
  );
}

const nodeTypes: NodeTypes = { chainNode: ChainNodeComp };

function Flow({ chain }: { chain: string }) {
  const initial = loadChain(chain);
  const [nodes, setNodes, onNodesChange] = useNodesState<ChainNodeT>(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initial.edges);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_PREFIX + chain, JSON.stringify({ nodes, edges }));
    } catch {
      /* ignore quota errors */
    }
  }, [chain, nodes, edges]);

  // Live quotes for target nodes: poll and patch each target node's changePct.
  const targetCodes = nodes.filter((n) => n.data.kind === "target" && n.data.code).map((n) => n.data.code as string);
  const codesKey = Array.from(new Set(targetCodes)).join(",");
  useEffect(() => {
    if (!codesKey) return;
    let active = true;
    const codes = codesKey.split(",");
    const pull = async () => {
      try {
        const { toTencentCode } = await import("@/lib/cn-market");
        const wire = await api.getQuotes(codes.map(toTencentCode));
        if (!active || wire.stale) return;
        setNodes((nds) =>
          nds.map((n) => {
            const code = n.data.code as string | undefined;
            if (n.data.kind !== "target" || !code) return n;
            const q = wire.quotes[toTencentCode(code)];
            return q ? { ...n, data: { ...n.data, changePct: q.change_pct } } : n;
          }),
        );
      } catch {
        /* keep nodes as-is on failure */
      }
    };
    pull();
    const id = window.setInterval(pull, 30_000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, [codesKey, setNodes]);

  const onConnect = useCallback((c: Connection) => setEdges((eds) => addEdge(c, eds)), [setEdges]);

  const addNode = (kind: ChainKind) => {
    const id = `n${Date.now()}`;
    setNodes((nds) =>
      nds.concat({
        id,
        type: "chainNode",
        position: { x: 120 + Math.random() * 240, y: 80 + Math.random() * 240 },
        data: { kind, label: KIND_LABEL[kind], desc: "双击编辑文字" },
      }),
    );
  };

  const deleteSelected = () => {
    setNodes((nds) => nds.filter((n) => !n.selected));
    setEdges((eds) => eds.filter((e) => !e.selected));
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">添加节点:</span>
        {KINDS.map((kind) => (
          <button
            key={kind}
            type="button"
            onClick={() => addNode(kind)}
            className={cn("inline-flex items-center gap-1 rounded-md border-2 px-2 py-1 text-xs font-medium", KIND_CLASS[kind])}
          >
            <Plus className="h-3 w-3" /> {KIND_LABEL[kind]}
          </button>
        ))}
        <button
          type="button"
          onClick={deleteSelected}
          className="inline-flex items-center gap-1 rounded-md border bg-card px-2 py-1 text-xs text-muted-foreground hover:text-danger"
        >
          <Trash2 className="h-3 w-3" /> 删除选中
        </button>
        <span className="ml-auto text-xs text-muted-foreground">
          提示: 双击节点编辑文字, 拖动节点上的小圆点连线, Del 键删除选中
        </span>
      </div>

      <div className="h-[64vh] overflow-hidden rounded-xl border bg-card">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          deleteKeyCode={["Backspace", "Delete"]}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} />
          <Controls />
          <MiniMap pannable zoomable className="!bg-muted" />
        </ReactFlow>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs">
        {KINDS.map((kind) => (
          <span key={kind} className="inline-flex items-center gap-1 text-muted-foreground">
            <span className={cn("h-2.5 w-2.5 rounded-full", KIND_DOT[kind])} />
            {KIND_LABEL[kind]}
          </span>
        ))}
      </div>
    </div>
  );
}

export function LogicChain() {
  const [chain, setChain] = useState(DEFAULT_CHAIN);
  const [topicInput, setTopicInput] = useState(DEFAULT_CHAIN);
  const [presets, setPresets] = useState<string[]>(() => loadPersisted(PRESETS_STORAGE_KEY, CHAIN_PRESETS));
  const [genVersion, setGenVersion] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestedTopics, setSuggestedTopics] = useState<string[]>([]);
  const [genError, setGenError] = useState<string | null>(null);
  const [suggestError, setSuggestError] = useState<string | null>(null);

  const updatePresets = useCallback((updater: (prev: string[]) => string[]) => {
    setPresets((prev) => {
      const next = updater(prev);
      savePersisted(PRESETS_STORAGE_KEY, next);
      return next;
    });
  }, []);

  const selectTopic = (name: string) => {
    setChain(name);
    setTopicInput(name);
    setGenVersion((v) => v + 1);
  };

  const ensurePreset = (name: string) => {
    updatePresets((p) => (p.includes(name) ? p : [...p, name]));
  };

  const deletePreset = (name: string) => {
    if (presets.length <= 1) return;
    clearPersisted(`logic-chain:${name}`);
    const next = presets.filter((p) => p !== name);
    updatePresets((prev) => prev.filter((p) => p !== name));
    setSuggestedTopics((prev) => prev.filter((t) => t !== name));
    if (chain === name) {
      selectTopic(next[0] ?? DEFAULT_CHAIN);
    }
  };

  const applyCustomTopic = () => {
    const name = topicInput.trim();
    if (!name) return;
    ensurePreset(name);
    selectTopic(name);
  };

  const newChain = () => {
    const name = `新建链 ${presets.length + 1}`;
    ensurePreset(name);
    selectTopic(name);
  };

  const suggestTopics = async () => {
    setSuggesting(true);
    setSuggestError(null);
    try {
      const wire = await api.suggestLogicChainTopics(topicInput.trim());
      if (wire.error || wire.topics.length === 0) {
        setSuggestError(wire.error || "未能推荐主题");
        return;
      }
      setSuggestedTopics(wire.topics);
      updatePresets((prev) => {
        const merged = [...prev];
        for (const t of wire.topics) {
          if (!merged.includes(t)) merged.push(t);
        }
        return merged;
      });
    } catch (e) {
      setSuggestError(formatAgentError(e, "推荐"));
    } finally {
      setSuggesting(false);
    }
  };

  const generate = async () => {
    setGenerating(true);
    setGenError(null);
    try {
      const wire = await api.generateLogicChain(chain);
      if (wire.error || wire.nodes.length === 0) {
        setGenError(wire.error || "未能生成逻辑链");
      } else {
        const laid = layoutGenerated(wire.nodes, wire.edges);
        localStorage.setItem(STORAGE_PREFIX + chain, JSON.stringify(laid));
        setGenVersion((v) => v + 1); // remount Flow to load the generated graph
      }
    } catch (e) {
      setGenError(formatAgentError(e, "生成"));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1400px] p-6">
      <div className="mb-3">
        <p className="mb-2 text-xs text-muted-foreground">预设主题（点击切换 · × 删除，至少保留 1 条）</p>
        <div className="flex flex-wrap gap-1.5">
          {presets.map((p) => {
            const active = chain === p;
            return (
              <div
                key={p}
                className={cn(
                  "inline-flex items-stretch overflow-hidden rounded-md border text-sm transition-colors",
                  active ? "border-primary bg-primary text-primary-foreground" : "bg-card text-muted-foreground",
                )}
              >
                <button
                  type="button"
                  onClick={() => selectTopic(p)}
                  className={cn(
                    "max-w-[220px] truncate px-3 py-1 text-left hover:opacity-90",
                    !active && "hover:text-foreground",
                  )}
                  title={p}
                >
                  {p}
                </button>
                {presets.length > 1 && (
                  <button
                    type="button"
                    onClick={() => deletePreset(p)}
                    className={cn(
                      "inline-flex items-center border-l px-1.5 hover:bg-black/10",
                      active ? "border-primary-foreground/30" : "border-border hover:text-danger",
                    )}
                    aria-label={`删除主题 ${p}`}
                    title="删除此主题"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            );
          })}
          <button
            type="button"
            onClick={newChain}
            className="rounded-md border border-dashed px-3 py-1 text-sm text-muted-foreground hover:text-foreground"
          >
            + 新建链
          </button>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="flex min-w-[280px] flex-1 flex-col gap-1">
          <span className="text-xs text-muted-foreground">自定义主题</span>
          <input
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applyCustomTopic()}
            placeholder="输入逻辑链主题，如「储能政策→锂电链受益」"
            className="rounded-md border bg-background px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
        </label>
        <button
          type="button"
          onClick={applyCustomTopic}
          className="rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          应用主题
        </button>
        <button
          type="button"
          onClick={suggestTopics}
          disabled={suggesting}
          className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5 text-sm text-primary hover:bg-primary/10 disabled:opacity-60"
        >
          {suggesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Agent 推荐主题
        </button>
      </div>

      {suggestedTopics.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted-foreground">推荐:</span>
          {suggestedTopics.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => selectTopic(t)}
              className="rounded-full border border-dashed border-primary/40 px-2.5 py-0.5 text-xs text-primary hover:bg-primary/5"
            >
              {t}
            </button>
          ))}
        </div>
      )}
      {suggestError && <p className="mb-3 text-xs text-danger">{suggestError}</p>}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={generate}
          disabled={generating}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
        >
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {generating ? "Agent 联网研究中…" : "用 Agent 生成本链"}
        </button>
        <span className="text-xs text-muted-foreground">
          当前主题「{chain}」· 未 Agent 生成时显示骨架链（触发→传导→板块→标的）· 生成后覆盖并本地缓存
        </span>
        {genError && <span className="text-xs text-danger">{genError}</span>}
      </div>

      <ReactFlowProvider>
        <Flow key={`${chain}#${genVersion}`} chain={chain} />
      </ReactFlowProvider>
    </div>
  );
}
