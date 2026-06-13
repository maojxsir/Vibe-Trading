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
import { fmtPct } from "@/lib/cn-market";
import { loadPersisted, savePersisted } from "@/lib/persist";
import { cn } from "@/lib/utils";
import {
  formatMarketCap,
  formatScanTotals,
  formatSignalSummary,
  hasActiveVeto,
  REQUIRED_SIGNAL_KEYS,
  SIGNAL_KEYS,
  SIGNAL_LABELS,
  type ScreenerItem,
  type ScreenerPayload,
  type ScreenerStatus,
} from "@/types/screener";

const OPPORTUNITIES_STORE = "opportunities";
const POLL_MS = 2000;

type SortKey =
  | "name"
  | "score"
  | "position_pct"
  | "market_cap"
  | "price"
  | "pe_ttm"
  | "quarter_growth";
type SortDir = "asc" | "desc";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function membershipTone(
  status: string,
): "success" | "danger" | "neutral" {
  if (status === "新增") return "success";
  if (status === "删除") return "danger";
  return "neutral";
}

function SignalMiniBars({ signals }: { signals: ScreenerItem["signals"] }) {
  return (
    <div className="flex items-end gap-1" title={formatSignalSummary(signals)}>
      {SIGNAL_KEYS.map((key) => {
        const value = Math.max(0, Math.min(1, signals[key] ?? 0));
        return (
          <div key={key} className="flex flex-col items-center gap-0.5">
            <div className="h-8 w-2 overflow-hidden rounded-sm bg-muted">
              <div
                className="w-full rounded-sm bg-primary transition-all"
                style={{ height: `${value * 100}%`, marginTop: `${(1 - value) * 100}%` }}
              />
            </div>
            <span
              className={cn(
                "text-[9px] leading-none",
                REQUIRED_SIGNAL_KEYS.includes(key as (typeof REQUIRED_SIGNAL_KEYS)[number])
                  ? "font-medium text-foreground"
                  : "text-muted-foreground",
              )}
            >
              {SIGNAL_LABELS[key]}
              {REQUIRED_SIGNAL_KEYS.includes(key as (typeof REQUIRED_SIGNAL_KEYS)[number]) ? "*" : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
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
          "inline-flex items-center gap-0.5 hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground",
        )}
      >
        {label}
        {active && <span className="text-[10px]">{dir === "asc" ? "↑" : "↓"}</span>}
      </button>
    </th>
  );
}

export function Screener() {
  const navigate = useNavigate();
  const [payload, setPayload] = useState<ScreenerPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scanStatus, setScanStatus] = useState<ScreenerStatus | null>(null);
  const [researchingCode, setResearchingCode] = useState<string | null>(null);
  const [chartTarget, setChartTarget] = useState<StockChartTarget | null>(null);

  const [minScore, setMinScore] = useState(0);
  const [hideUntradable, setHideUntradable] = useState(false);
  const [hideVetoed, setHideVetoed] = useState(false);

  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const loadData = useCallback(async (): Promise<ScreenerPayload | null> => {
    try {
      const data = await api.getScreener();
      setPayload(data);
      return data;
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "加载打板扫描失败");
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
      if (hideUntradable && row.untradable) return false;
      if (hideVetoed && hasActiveVeto(row.vetoes)) return false;
      return true;
    });
  }, [payload?.items, minScore, hideUntradable, hideVetoed]);

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
        case "position_pct":
          cmp = a.position_pct - b.position_pct;
          break;
        case "market_cap":
          cmp = (a.market_cap ?? 0) - (b.market_cap ?? 0);
          break;
        case "price":
          cmp = (a.price ?? 0) - (b.price ?? 0);
          break;
        case "pe_ttm":
          cmp = (a.pe_ttm ?? 0) - (b.pe_ttm ?? 0);
          break;
        case "quarter_growth":
          cmp = (a.quarter_growth ?? 0) - (b.quarter_growth ?? 0);
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
      const status = await api.getScreenerStatus();
      setScanStatus(status);
      if (status.state === "running") {
        await sleep(POLL_MS);
        return pollScanStatus();
      }
      if (status.state === "failed") {
        toast.error(status.message || "打板扫描失败");
      } else if (status.state === "done") {
        const data = await loadData();
        if (data && !data.stale) {
          toast.success(formatScanTotals(data));
        } else {
          toast.success("打板扫描完成");
        }
        return;
      }
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "获取扫描状态失败");
    }
  }, [loadData]);

  const handleRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await api.refreshScreener();
      await pollScanStatus();
    } catch (e) {
      if (e instanceof Error && e.message.includes("already running")) {
        await pollScanStatus();
      } else {
        toast.error(e instanceof Error ? e.message : "触发扫描失败");
      }
    } finally {
      setRefreshing(false);
    }
  };

  const researchOne = async (row: ScreenerItem) => {
    setResearchingCode(row.code);
    try {
      const summary = formatSignalSummary(row.signals);
      const prompt =
        `请联网研究以下 A 股打板候选标的，评估四信号与连板潜力。\n\n` +
        `标的：${row.name}(${row.code})\n板块：${row.board}\n` +
        `${row.industry ? `行业：${row.industry}\n` : ""}` +
        `${row.market_cap ? `总市值：${formatMarketCap(row.market_cap)}\n` : ""}` +
        `${row.main_business ? `主营业务：${row.main_business}\n` : ""}` +
        `综合评分：${row.score.toFixed(1)}\n` +
        `四信号：${summary}\n位置分位：${row.position_pct.toFixed(1)}%\n` +
        `${row.untradable ? "状态：不可交易（一字/停牌等）\n" : ""}` +
        `\n要求：\n1. 用 web_search 检索最新题材、连板逻辑、资金与风险；\n` +
        `2. 评估四信号是否支持次日打板/接力；\n` +
        `3. 给出买点、止损与需跟踪的盘口/题材指标；\n` +
        `4. 用中文，结构化输出。`;
      await launchAgentFromPage(
        navigate,
        `打板·${row.name}`,
        prompt,
        "收到，正在检索打板逻辑与四信号验证…",
      );
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "无法启动 Agent 研究（需后端运行）");
    } finally {
      setResearchingCode(null);
    }
  };

  const addToOpportunities = (row: ScreenerItem, e: React.MouseEvent) => {
    e.stopPropagation();
    const existing = loadPersisted(OPPORTUNITIES_STORE, opportunitiesSeed);
    const next: Opportunity = {
      name: row.name,
      code: row.code,
      sector: row.industry || row.board,
      trigger: formatSignalSummary(row.signals),
      target: 0,
      score: Math.round(row.score),
      status: "关注",
    };
    savePersisted(OPPORTUNITIES_STORE, [...existing, next]);
    toast.success(`已加入机会池：${row.name}`);
  };

  const isScanning = refreshing || scanStatus?.state === "running";

  return (
    <div className="mx-auto max-w-7xl p-6">
      <PageHeader
        title="打板扫描"
        subtitle="A 股打板筛选：必选涨停+量能，可选跳空+连阳；排除 ST 与已大涨高位"
        meta={
          <>
            {payload?.tradeDate && (
              <Badge tone="neutral">交易日 {payload.tradeDate}</Badge>
            )}
            {payload && !payload.stale && (
              <Badge tone="primary">{formatScanTotals(payload)}</Badge>
            )}
            {payload?.source && !payload.stale && (
              <Badge tone="info">数据源 {payload.source}</Badge>
            )}
            {payload?.stale && (
              <Badge tone="warning">
                {payload.stale_reason === "policy_updated"
                  ? "策略已更新，请重新扫描"
                  : "数据过期"}
              </Badge>
            )}
            {payload?.degraded && !payload?.stale && <Badge tone="warning">降级模式</Badge>}
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
          <span className="text-muted-foreground whitespace-nowrap">最低评分 {minScore}</span>
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
          <input
            type="checkbox"
            checked={hideUntradable}
            onChange={(e) => setHideUntradable(e.target.checked)}
          />
          隐藏不可交易
        </label>
        <label className="flex items-center gap-1.5 text-muted-foreground">
          <input
            type="checkbox"
            checked={hideVetoed}
            onChange={(e) => setHideVetoed(e.target.checked)}
          />
          隐藏否决项
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
            {payload?.stale_reason === "policy_updated"
              ? "筛选策略已更新（排除 ST、必选涨停+量能），请点击「刷新扫描」重新生成结果"
              : payload?.stale
                ? "暂无扫描结果，请点击「刷新扫描」生成数据"
                : "无符合筛选条件的标的"}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs">
                  <SortHeader label="名称/代码" active={sortKey === "name"} dir={sortDir} onClick={() => handleSort("name")} />
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">行业/主营业务</th>
                  <SortHeader label="现价" active={sortKey === "price"} dir={sortDir} onClick={() => handleSort("price")} align="right" />
                  <SortHeader label="PE(TTM)" active={sortKey === "pe_ttm"} dir={sortDir} onClick={() => handleSort("pe_ttm")} align="right" />
                  <SortHeader label="季度增速" active={sortKey === "quarter_growth"} dir={sortDir} onClick={() => handleSort("quarter_growth")} align="right" />
                  <SortHeader label="市值" active={sortKey === "market_cap"} dir={sortDir} onClick={() => handleSort("market_cap")} align="right" />
                  <SortHeader label="评分" active={sortKey === "score"} dir={sortDir} onClick={() => handleSort("score")} align="right" />
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">四信号</th>
                  <SortHeader
                    label="位置%"
                    active={sortKey === "position_pct"}
                    dir={sortDir}
                    onClick={() => handleSort("position_pct")}
                    align="right"
                  />
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">状态</th>
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
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-foreground">{row.name}</div>
                      <div className="text-xs tabular-nums text-muted-foreground">{row.code}</div>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      <div className="max-w-[260px]">
                        {row.industry && (
                          <div className="text-xs font-medium text-foreground">{row.industry}</div>
                        )}
                        <span className="block truncate text-xs" title={row.main_business || ""}>
                          {row.main_business || (row.industry ? "" : "—")}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-foreground">
                      {row.price != null ? row.price.toFixed(2) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                      {row.pe_ttm != null ? row.pe_ttm.toFixed(1) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      {row.quarter_growth != null ? (
                        <span className={cn(row.quarter_growth >= 0 ? "text-danger" : "text-success")}>
                          {row.quarter_growth >= 0 ? "+" : ""}
                          {row.quarter_growth.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                      {formatMarketCap(row.market_cap)}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums">
                      <span className={cn("font-medium", row.score >= 85 ? "text-danger" : "text-foreground")}>
                        {row.score.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <SignalMiniBars signals={row.signals} />
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                      {fmtPct(row.position_pct)}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap items-center gap-1">
                        {row.membership_status && (
                          <Badge tone={membershipTone(row.membership_status)}>
                            {row.membership_status}
                          </Badge>
                        )}
                        {row.untradable && <Badge tone="warning">不可交易</Badge>}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => researchOne(row)}
                          disabled={researchingCode !== null}
                          className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 disabled:opacity-50"
                          title="让 Agent 联网研究该标的"
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
                          title="加入机会清单"
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
          未命中 {payload.filtered_count.toLocaleString("zh-CN")} 只（未满足必选信号或否决）
          {" · "}
          数据缺失跳过 {payload.skipped.toLocaleString("zh-CN")} 只
          {payload.degraded && <span className="ml-1 text-warning">（部分信号数据降级，评分仅供参考）</span>}
        </p>
      )}
      {payload && !loading && payload.stale && (
        <p className="mt-4 text-xs text-muted-foreground">
          {payload.stale_reason === "policy_updated"
            ? "当前展示的是旧版扫描缓存，已按新策略作废。重新扫描后将按「排除 ST + 必选涨停/量能」筛选。"
            : "暂无有效扫描结果，请点击「刷新扫描」。"}
        </p>
      )}

      <StockChartDrawer target={chartTarget} onClose={() => setChartTarget(null)} />
    </div>
  );
}
