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
import { Plus, Trash2, Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { changeColorClass, fmtPct } from "@/lib/cn-market";
import { api, type LogicChainNodeWire } from "@/lib/api";
import {
  CHAIN_PRESETS,
  DEFAULT_CHAIN,
  defaultNodes,
  defaultEdges,
  KIND_LABEL,
  KIND_CLASS,
  KIND_DOT,
  type ChainKind,
  type ChainNode as ChainNodeT,
} from "@/data/logicChainSeed";

const STORAGE_PREFIX = "vt-logic-chain:";
const KINDS: ChainKind[] = ["trigger", "transmit", "sector", "target"];
const COLUMN_X: Record<ChainKind, number> = { trigger: 0, transmit: 340, sector: 680, target: 1020 };

function loadChain(chain: string): { nodes: ChainNodeT[]; edges: Edge[] } {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + chain);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore corrupt cache */
  }
  if (chain === DEFAULT_CHAIN) return { nodes: defaultNodes, edges: defaultEdges };
  return { nodes: [], edges: [] };
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
  const [presets, setPresets] = useState(CHAIN_PRESETS);
  const [genVersion, setGenVersion] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const newChain = () => {
    const name = `新建链 ${presets.length + 1}`;
    setPresets((p) => [...p, name]);
    setChain(name);
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
      const detail = e instanceof Error ? e.message : "未知错误";
      setGenError(`生成失败: ${detail}（需后端运行且已配置 LLM key）`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1400px] p-6">
      <div className="mb-3 flex flex-wrap gap-1.5">
        {presets.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setChain(p)}
            className={cn(
              "rounded-md border px-3 py-1 text-sm transition-colors",
              chain === p ? "border-primary bg-primary text-primary-foreground" : "bg-card text-muted-foreground hover:text-foreground",
            )}
          >
            {p}
          </button>
        ))}
        <button
          type="button"
          onClick={newChain}
          className="rounded-md border border-dashed px-3 py-1 text-sm text-muted-foreground hover:text-foreground"
        >
          + 新建链
        </button>
      </div>

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
          调用 Vibe-Trading Agent（web_search 联网）生成「{chain}」的真实逻辑链，标的节点挂实时行情
        </span>
        {genError && <span className="text-xs text-danger">{genError}</span>}
      </div>

      <ReactFlowProvider>
        <Flow key={`${chain}#${genVersion}`} chain={chain} />
      </ReactFlowProvider>
    </div>
  );
}
