import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useSearchParams } from "react-router-dom";
import { BarChart3, Bot, Moon, Sun, Plus, Trash2, Pencil, MessageSquare, ChevronsLeft, ChevronsRight, Settings, Layers, Loader2, LayoutDashboard, ClipboardList, ListChecks, Share2, Cpu, Zap, Compass, Activity, Newspaper, Grid3x3, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useDarkMode } from "@/hooks/useDarkMode";
import { MarketColorSchemeProvider } from "@/contexts/MarketColorSchemeContext";
import { api, type SessionItem } from "@/lib/api";
import { useAgentStore } from "@/stores/agent";
import { ConnectionBanner } from "@/components/layout/ConnectionBanner";

// Bump on each release; one place keeps the footer in sync with package.json.
const APP_VERSION = "v0.1.9";

function formatSessionTime(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (24 * 60 * 60 * 1000));
  if (diffDays <= 0) return "今天";
  if (diffDays === 1) return "昨天";
  if (diffDays < 7) return `${diffDays} 天前`;
  return date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Home" },
  { to: "/holdings", icon: ClipboardList, label: "持仓决策" },
  { to: "/opportunities", icon: ListChecks, label: "机会清单" },
  { to: "/screener", icon: TrendingUp, label: "打板扫描" },
  { to: "/logic-chain", icon: Share2, label: "逻辑链" },
  { to: "/agent", icon: Bot, label: "Agent" },
  { to: "/humanoid", icon: Cpu, label: "人形机器人" },
  { to: "/ai-compute", icon: Zap, label: "AI算力" },
  { to: "/serenity", icon: Compass, label: "Serenity 方法论" },
  { to: "/events", icon: Activity, label: "事件概率" },
  { to: "/news", icon: Newspaper, label: "新闻" },
  { to: "/alpha-zoo", icon: Layers, label: "Alpha Zoo" },
  { to: "/correlation", icon: Grid3x3, label: "Correlation Matrix" },
];

export function Layout() {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const { dark, toggle } = useDarkMode();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const sseStatus = useAgentStore(s => s.sseStatus);
  const sseRetryAttempt = useAgentStore(s => s.sseRetryAttempt);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("qa-sidebar") === "collapsed");

  const activeSessionId = searchParams.get("session");
  const streamingSessionId = useAgentStore(s => s.streamingSessionId);

  useEffect(() => {
    localStorage.setItem("qa-sidebar", collapsed ? "collapsed" : "expanded");
  }, [collapsed]);

  const loadSessions = () => {
    api.listSessions()
      .then((list) => setSessions(Array.isArray(list) ? list : []))
      .catch(() => {})
      .finally(() => setSessionsLoading(false));
  };

  // Load sessions on mount. Also refresh when navigating TO /agent or when
  // the active session changes (covers new session creation from Agent).
  const isAgentPage = pathname.startsWith("/agent");
  useEffect(() => { loadSessions(); }, [isAgentPage, activeSessionId]);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const deleteSession = async (sid: string) => {
    try {
      await api.deleteSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
    } catch { /* ignore */ }
    setDeleteTarget(null);
  };

  const renameSession = async (sid: string) => {
    if (!renameValue.trim()) { setRenameTarget(null); return; }
    try {
      await api.renameSession(sid, renameValue.trim());
      setSessions((prev) => prev.map((s) => s.session_id === sid ? { ...s, title: renameValue.trim() } : s));
    } catch { /* ignore */ }
    setRenameTarget(null);
  };

  return (
    <MarketColorSchemeProvider>
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className={cn(
        "flex h-screen shrink-0 flex-col overflow-hidden border-r bg-card transition-all duration-200",
        collapsed ? "w-12" : "w-72"
      )}>
        {/* Brand */}
        <div className={cn("shrink-0 border-b", collapsed ? "flex justify-center p-2" : "p-4")}>
          <Link to="/" className={cn("flex items-center text-base font-bold tracking-tight", collapsed ? "justify-center" : "gap-2")}>
            <BarChart3 className="h-5 w-5 shrink-0 text-primary" />
            {!collapsed && "Vibe-Trading"}
          </Link>
        </div>

        {/* Nav — fills space above sessions (sessions capped at 30%) */}
        <nav
          className={cn(
            "overflow-y-auto overscroll-contain",
            collapsed ? "max-h-none shrink-0 p-1" : "min-h-0 flex-1 space-y-0.5 p-2",
          )}
        >
          {NAV.map(({ to, icon: Icon, label }) => {
            const text = label;
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center rounded-md text-sm transition-colors",
                  collapsed ? "justify-center p-2" : "gap-3 px-3 py-2",
                  (to === "/" ? pathname === "/" : pathname.startsWith(to))
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                title={collapsed ? text : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {!collapsed && text}
              </Link>
            );
          })}
        </nav>

        {/* Sessions — hidden when collapsed */}
        {!collapsed && (
          <div className="flex h-[30%] min-h-0 shrink-0 flex-col overflow-hidden border-t">
            <div className="flex shrink-0 items-center justify-between px-3 py-2.5">
              <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                会话
              </span>
              <Link
                to="/agent"
                className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                title="新建会话"
              >
                <Plus className="h-3.5 w-3.5" />
                新建
              </Link>
            </div>

            <div className="min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain px-2 pb-2">
              {sessionsLoading ? (
                <div className="space-y-2 px-1 py-1">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-11 rounded-lg bg-muted/50 animate-pulse" />
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <p className="px-2 py-3 text-sm text-muted-foreground/70">暂无会话，点击「新建」开始</p>
              ) : null}
              {sessions.map((s) => {
                const isActive = s.session_id === activeSessionId;
                const isDeleting = deleteTarget === s.session_id;
                const isRenaming = renameTarget === s.session_id;
                const sessionTime = formatSessionTime(s.updated_at || s.created_at);
                return (
                  <div
                    key={s.session_id}
                    className={cn(
                      "group relative rounded-lg border border-transparent transition-colors",
                      isActive && "border-primary/20 bg-primary/5",
                      !isActive && "hover:border-border/60 hover:bg-muted/40",
                    )}
                  >
                    {isRenaming ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") renameSession(s.session_id); if (e.key === "Escape") setRenameTarget(null); }}
                        onBlur={() => renameSession(s.session_id)}
                        className="w-full rounded-lg border border-primary bg-background px-3 py-2.5 text-sm outline-none"
                      />
                    ) : (
                      <Link
                        to={`/agent?session=${s.session_id}`}
                        className={cn(
                          "block min-w-0 rounded-lg py-2.5 pl-3 pr-16 text-sm transition-colors",
                          isActive
                            ? "text-primary font-medium"
                            : "text-foreground/90 hover:text-foreground",
                        )}
                        title={s.title || s.session_id}
                      >
                        <span className="flex items-start gap-2">
                          {streamingSessionId === s.session_id ? (
                            <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" />
                          ) : (
                            <span className={cn(
                              "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                              isActive ? "bg-primary" : "bg-muted-foreground/40",
                            )} />
                          )}
                          <span className="min-w-0 flex-1">
                            <span className="block truncate leading-snug">
                              {s.title || s.session_id.slice(0, 16)}
                            </span>
                            {sessionTime && (
                              <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                                {sessionTime}
                              </span>
                            )}
                          </span>
                        </span>
                      </Link>
                    )}
                    {!isRenaming && isDeleting ? (
                      <div className="absolute inset-y-0 right-1 flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => deleteSession(s.session_id)}
                          className="rounded-md bg-danger/10 px-2 py-1 text-xs font-medium text-danger hover:bg-danger/20"
                        >
                          确认
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(null)}
                          className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
                        >
                          取消
                        </button>
                      </div>
                    ) : !isRenaming ? (
                      <div className={cn(
                        "absolute inset-y-0 right-1 flex items-center gap-0.5 transition-opacity",
                        isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100",
                      )}>
                        <button
                          type="button"
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setRenameTarget(s.session_id); setRenameValue(s.title || ""); }}
                          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                          title="重命名"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteTarget(s.session_id); }}
                          className="rounded-md p-1.5 text-muted-foreground hover:bg-danger/10 hover:text-danger"
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Spacer when collapsed */}
        {collapsed && <div className="min-h-0 flex-1" />}

        {/* Footer — pinned below nav + sessions */}
        <div className={cn("shrink-0 border-t bg-card", collapsed ? "flex flex-col items-center gap-1 p-1" : "space-y-2 p-3")}>
          {collapsed ? (
            <>
              <Link
                to="/settings"
                className="rounded p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                title="Settings"
              >
                <Settings className="h-3.5 w-3.5" />
              </Link>
              <button onClick={toggle} className="rounded p-1.5 text-muted-foreground transition-colors hover:text-foreground" title={dark ? "Light" : "Dark"}>
                {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              </button>
              <button onClick={() => setCollapsed(false)} className="rounded p-1.5 text-muted-foreground transition-colors hover:text-foreground" title="Expand">
                <ChevronsRight className="h-3.5 w-3.5" />
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 flex-1 items-center gap-1">
                  <Link
                    to="/settings"
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs transition-colors",
                      pathname.startsWith("/settings")
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <Settings className="h-3.5 w-3.5 shrink-0" />
                    Settings
                  </Link>
                  <button
                    type="button"
                    onClick={toggle}
                    className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    {dark ? <Sun className="h-3.5 w-3.5 shrink-0" /> : <Moon className="h-3.5 w-3.5 shrink-0" />}
                    {dark ? "Light" : "Dark"}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setCollapsed(true)}
                  className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
                  title="Collapse"
                >
                  <ChevronsLeft className="h-3.5 w-3.5" />
                </button>
              </div>
              <p className="text-xs text-muted-foreground/60">{APP_VERSION}</p>
            </>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ConnectionBanner status={sseStatus} retryAttempt={sseRetryAttempt} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
    </MarketColorSchemeProvider>
  );
}
