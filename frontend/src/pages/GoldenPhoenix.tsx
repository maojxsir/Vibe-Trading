import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Bot, Loader2, Plus, RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { Badge } from "@/components/dashboard/Badge";
import { StockChartDrawer } from "@/components/market/StockChartDrawer";
import type { StockChartTarget } from "@/contexts/StockChartDrawerContext";
import { opportunitiesSeed, type Opportunity } from "@/data/opportunitiesSeed";
import { api } from "@/lib/api";
import { launchAgentFromPage } from "@/lib/agent-launch";
import { loadPersisted, savePersisted } from "@/lib/persist";
import { cn } from "@/lib/utils";
import {
  formatGoldenPhoenixSignals,
  formatGoldenPhoenixStatus,
  formatMarketCap,
  formatScanTotals,
  type GoldenPhoenixItem,
  type GoldenPhoenixPayload,
  type GoldenPhoenixStatus,
} from "@/types/goldenPhoenix";

const OPPORTUNITIES_STORE = "opportunities";
const POLL_MS = 2000;

type SortKey = "name" | "score" | "lifeline" | "callback_days" | "market_cap" | "price";
type SortDir = "asc" | "desc";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function SortHeader({
  label,
  active,
  dir,
  onClick,
  align = "left",
}: {
  label: string;
  active: boolean;
  dir: SortDir;
  onClick: () => void;
  align?: "left" | "right";
}) {
  return (
    <th className={cn("px-3 py-2 font-medium", align === "right" ? "text-right" : "text-left")}>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "inline-flex items-center gap-0.5 whitespace-nowrap hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        {active && <span className="text-[10px]">{dir === "asc" ? "↑" : "↓"}</span>}
      </button>
    </th>
  );
}

export function GoldenPhoenix() {
  const navigate = useNavigate();
  const [payload, setPayload] = useState<GoldenPhoenixPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scanStatus, setScanStatus] = useState<GoldenPhoenixStatus | null>(null);
  const [minScore, setMinScore] = useState(0);
  const [hideWatch, setHideWatch] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [chartTarget, setChartTarget] = useState<StockChartTarget | null>(null);
  const [researchingCode, setResearchingCode] = useState<string | null>(null);

  const loadData = useCallback(async (): Promise<GoldenPhoenixPayload | null> => {
    try {
      const data = await api.getGoldenPhoenix();
      setPayload(data);
      return data;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "加载失败");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "score" ? "desc" : "asc");
    }
  };

  const filteredItems = useMemo(() => {
    const items = payload?.items ?? [];
    return items.filter((row) => {
      if (row.score < minScore) return false;
      if (hideWatch && row.status === "watch") return false;
      return true;
    });
  }, [payload?.items, minScore, hideWatch]);

  const sortedItems = useMemo(() => {
    const rows = [...filteredItems];
    const dir = sortDir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.name.localeCompare(b.name, "zh-CN");
          break;
        case "score":
          cmp = a.score - b.score;
          break;
        case "lifeline":
          cmp = a.lifeline - b.lifeline;
          break;
        case "callback_days":
          cmp = a.callback_days - b.callback_days;
          break;
        case "market_cap":
          cmp = (a.market_cap ?? 0) - (b.market_cap ?? 0);
          break;
        case "price":
          cmp = (a.price ?? 0) - (b.price ?? 0);
          break;
        default: {
          const _exhaustive: never = sortKey;
          return _exhaustive;
        }
      }
      return cmp * dir;
    });
    return rows;
  }, [filteredItems, sortKey, sortDir]);

  const pollScanStatus = useCallback(async (): Promise<void> => {
    try {
      const status = await api.getGoldenPhoenixStatus();
      setScanStatus(status);
      if (status.state === "running") {
        await sleep(POLL_MS);
        return pollScanStatus();
      }
      if (status.state === "failed") {
        toast.error(status.message || "金凤凰扫描失败");
      } else if (status.state === "done") {
        const data = await loadData();
        if (data && !data.stale) {
          toast.success(formatScanTotals(data));
        } else {
          toast.success("金凤凰扫描完成");
        }
        return;
      }
      await loadData();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "扫描状态查询失败");
    } finally {
      setRefreshing(false);
    }
  }, [loadData]);

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const res = await api.refreshGoldenPhoenix();
      if (!res.accepted) {
        toast.message(res.message ?? "扫描已在进行中");
        await pollScanStatus();
        return;
      }
      toast.message("金凤凰扫描已开始…");
      await pollScanStatus();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "触发扫描失败");
      setRefreshing(false);
    }
  };

  const researchOne = async (row: GoldenPhoenixItem) => {
    setResearchingCode(row.code);
    try {
      const prompt =
        `请联网研究以下 A 股「涨停金凤凰」候选标的，评估 N 字涨停形态与连板潜力。\n\n` +
        `标的：${row.name}(${row.code})\n板块：${row.board}\n` +
        `${row.industry ? `行业：${row.industry}\n` : ""}` +
        `首板日：${row.t0_date}\n生命线：${row.lifeline}\n回调天数：${row.callback_days}\n` +
        `当前状态：${formatGoldenPhoenixStatus(row.status)}\n` +
        `综合评分：${row.score.toFixed(1)}\n` +
        `辅助信号：${formatGoldenPhoenixSignals(row.signals)}\n` +
        `\n要求：\n1. 验证首板后收盘价是否始终守住生命线；\n` +
        `2. 评估二板确认或蓄势待板的接力价值；\n` +
        `3. 给出买点、止损（生命线下方）与需跟踪的题材/盘口指标；\n` +
        `4. 用中文，结构化输出。`;
      await launchAgentFromPage(
        navigate,
        `金凤凰·${row.name}`,
        prompt,
        "收到，正在检索金凤凰形态与连板逻辑…",
      );
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "无法启动 Agent 研究（需后端运行）");
    } finally {
      setResearchingCode(null);
    }
  };

  const addToOpportunities = (row: GoldenPhoenixItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const existing = loadPersisted(OPPORTUNITIES_STORE, opportunitiesSeed);
    const next: Opportunity = {
      name: row.name,
      code: row.code,
      sector: row.industry || row.board,
      trigger: `${formatGoldenPhoenixStatus(row.status)} · ${formatGoldenPhoenixSignals(row.signals)}`,
      target: row.lifeline,
      score: Math.round(row.score),
      status: row.status === "confirmed" ? "待买" : "关注",
    };
    savePersisted(OPPORTUNITIES_STORE, [...existing, next]);
    toast.success(`已加入机会池：${row.name}`);
  };

  const isScanning = refreshing || scanStatus?.state === "running";

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="涨停金凤凰"
        subtitle="N字涨停筛选：首板不破高、回调3-9日、二板确认进场"
        meta={
          <>
            {payload?.tradeDate && <Badge tone="neutral">交易日 {payload.tradeDate}</Badge>}
            {payload && !payload.stale && <Badge tone="primary">{formatScanTotals(payload)}</Badge>}
            {payload?.source && !payload.stale && <Badge tone="info">数据源 {payload.source}</Badge>}
            {payload?.stale && (
              <Badge tone="warning">
                {payload.stale_reason === "policy_updated" ? "策略已更新，请重新扫描" : "数据过期"}
              </Badge>
            )}
            {payload?.updatedAt && (
              <span>更新 {new Date(payload.updatedAt).toLocaleString("zh-CN")}</span>
            )}
            {isScanning && (
              <Badge tone="primary">
                扫描中 {scanStatus?.progress ? `${scanStatus.progress}%` : "…"}
              </Badge>
            )}
          </>
        }
        actions={
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isScanning}
            className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            <RefreshCw className={cn("h-4 w-4", isScanning && "animate-spin")} />
            {isScanning ? "扫描中…" : "刷新扫描"}
          </button>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
        <label className="flex items-center gap-2">
          <span className="whitespace-nowrap text-muted-foreground">最低评分 {minScore}</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-32"
          />
        </label>
        <label className="flex items-center gap-1.5 text-muted-foreground">
          <input type="checkbox" checked={hideWatch} onChange={(e) => setHideWatch(e.target.checked)} />
          仅看二板确认
        </label>
        <span className="text-xs text-muted-foreground">
          当前显示 {sortedItems.length.toLocaleString("zh-CN")} /{" "}
          {(payload?.matched_count ?? payload?.items.length ?? 0).toLocaleString("zh-CN")} 条
        </span>
      </div>

      <Card>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            加载中…
          </div>
        ) : sortedItems.length === 0 ? (
          <p className="py-16 text-center text-sm text-muted-foreground">
            {payload?.stale ? "暂无扫描结果，请点击「刷新扫描」生成数据" : "无符合金凤凰形态的标的"}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs">
                  <SortHeader label="名称/代码" active={sortKey === "name"} dir={sortDir} onClick={() => handleSort("name")} />
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">行业</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">状态</th>
                  <SortHeader label="评分" active={sortKey === "score"} dir={sortDir} onClick={() => handleSort("score")} align="right" />
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">首板日</th>
                  <SortHeader label="生命线" active={sortKey === "lifeline"} dir={sortDir} onClick={() => handleSort("lifeline")} align="right" />
                  <SortHeader label="回调" active={sortKey === "callback_days"} dir={sortDir} onClick={() => handleSort("callback_days")} align="right" />
                  <SortHeader label="现价" active={sortKey === "price"} dir={sortDir} onClick={() => handleSort("price")} align="right" />
                  <SortHeader label="市值" active={sortKey === "market_cap"} dir={sortDir} onClick={() => handleSort("market_cap")} align="right" />
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">辅助信号</th>
                  <th className="px-3 py-2 text-right font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map((row) => (
                  <tr
                    key={`${row.code}-${row.trade_date}`}
                    onClick={() => setChartTarget({ code: row.code, name: row.name })}
                    className="cursor-pointer border-b border-border/60 last:border-0 hover:bg-muted/40"
                  >
                    <td className="whitespace-nowrap px-3 py-2.5">
                      <div className="font-medium text-foreground">{row.name}</div>
                      <div className="text-xs tabular-nums text-muted-foreground">{row.code}</div>
                    </td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">{row.industry || row.board || "—"}</td>
                    <td className="px-3 py-2.5">
                      <Badge tone={row.status === "confirmed" ? "danger" : "neutral"}>
                        {formatGoldenPhoenixStatus(row.status)}
                      </Badge>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      <span className={cn("font-medium", row.score >= 90 ? "text-danger" : "text-foreground")}>
                        {row.score.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-muted-foreground">{row.t0_date}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-foreground">{row.lifeline.toFixed(2)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">{row.callback_days}天</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-foreground">
                      {row.price != null ? row.price.toFixed(2) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                      {formatMarketCap(row.market_cap)}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-muted-foreground">
                      {formatGoldenPhoenixSignals(row.signals)}
                    </td>
                    <td className="px-3 py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => researchOne(row)}
                          disabled={researchingCode !== null}
                          className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50"
                        >
                          {researchingCode === row.code ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Bot className="h-3.5 w-3.5" />
                          )}
                          Agent 研究
                        </button>
                        <button
                          type="button"
                          onClick={(e) => addToOpportunities(row, e)}
                          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                        >
                          <Plus className="h-3.5 w-3.5" />
                          加入机会池
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {payload && !loading && !payload.stale && (
        <p className="mt-4 text-xs text-muted-foreground">
          {formatScanTotals(payload)}
          {" · "}
          未命中 {payload.filtered_count.toLocaleString("zh-CN")} 只
          {" · "}
          数据缺失跳过 {payload.skipped.toLocaleString("zh-CN")} 只
        </p>
      )}

      <StockChartDrawer target={chartTarget} onClose={() => setChartTarget(null)} />
    </div>
  );
}
