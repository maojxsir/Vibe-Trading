# 设计文档：将 Vibe-Trading 前端改造为「A股投研工作台」

- 日期：2026-06-06
- 状态：待用户评审
- 工作目录：`/Users/maojianxin/my_test/Vibe-Trading`（已 clone）
- 目标：在不破坏现有后端 / CLI / 现有页面的前提下，把 Vibe-Trading 的 React 前端改造成 4 张截图所展示的「A股投研工作台」样子，新增 9 个页面并重做左侧导航。

---

## 1. 背景与目标

Vibe-Trading 现有前端是一个 React 19 + Vite + TypeScript 的本地 Web 应用（SPA），后端为 FastAPI。现有页面：Home、Agent、AlphaZoo、Correlation、Compare、RunDetail、Settings。

用户提供 4 张截图，描述了一个面向 A 股的投研工作台：
- **图1（市场总览 / Home）**：浅色主题。大盘指数卡片 + 人形机器人/AI算力两张「核心标的」实时行情表，标注「腾讯, 30s 自动刷新」。
- **图2（AI算力）**：深色主题。AI 算力产业链深度分析，多 Tab + 核心标的横向对比表。
- **图3（人形机器人）**：深色主题。人形机器人产业链深度分析，多 Tab + 估值全景表。
- **图4（逻辑链）**：深色主题。可编辑的「逻辑链」节点图（触发因素→传导逻辑→受益板块→具体标的）。

**重要发现**：图1 是浅色、图2/3/4 是深色，差异来自应用**已有的明暗主题切换**（`.dark` class），并非每页单独配色。因此新页面直接复用现有 Tailwind 语义化 token 即可自动适配明暗两套主题。

### 目标（本次交付）
1. 重做左侧导航（13 项，含已有页面 + 9 个新页面），顺序与图标对齐截图。
2. 新增并实现 9 个页面（全部，不分期）：市场总览（替换 Home）、持仓决策、机会清单、逻辑链、人形机器人、AI算力、Serenity 方法论、事件概率、新闻。
3. 保留并继续可用：Agent、Alpha Zoo、Settings、Correlation Matrix。
4. 市场总览页对接**真实实时行情**（腾讯免费源，30s 轮询），并带**种子数据兜底**，保证断网/后端不可用时仍能渲染。
5. 行情涨跌颜色采用**中国习惯：红涨绿跌**（与仓库默认 success=绿/danger=红 相反，在新页面内单独处理）。

### 非目标（本次不做）
- 不做真实的产业链数据动态计算（图2/3 用人工整理的研究数据，作为种子内容）。
- 不做桌面可执行文件打包（仍是本地 Web 应用；如需 Tauri/Electron 后续单独立项）。
- 不改动后端 Agent / 回测 / Swarm / 交易连接器逻辑。
- 不做账户体系、持久化存储新页面的数据（持仓/逻辑链编辑先存 localStorage）。

---

## 2. 技术现状（已核对真实代码）

- 路由：`frontend/src/router.tsx`，`createBrowserRouter` + 懒加载，所有页面挂在 `<Layout>` 的 `<Outlet/>` 下。
- 导航：`frontend/src/components/layout/Layout.tsx` 顶部 `NAV` 数组驱动侧栏；侧栏还含 Sessions 列表 + 明暗切换 + 折叠。
- 主题：`frontend/src/index.css` 用 CSS 变量定义 `:root` / `.dark`；`tailwind.config.ts` 暴露 `background/card/primary/muted/border/success/danger/warning/info` 等语义色；`primary` 为橙色。
- 图表：依赖已含 `echarts@6`、`lucide-react`（图标）、`zustand`（状态）、`sonner`（toast）、`react-markdown`。
- 前端访问后端：`frontend/src/lib/api.ts` 用相对路径 `fetch`，开发期由 `vite.config.ts` 的 `PROXY_PATHS` 代理到 `http://localhost:8899`。
- 后端：`agent/api_server.py` 用 `@app.get(...)` 直接注册路由，另有 `agent/src/api/alpha_routes.py` 路由包样例。

---

## 3. 架构与改动清单

### 3.1 导航（侧栏）
改 `Layout.tsx` 的 `NAV` 数组为 13 项，顺序/图标对齐截图：

| 顺序 | label | 路由 | lucide 图标（建议） | 类型 |
|---|---|---|---|---|
| 1 | Home（市场总览） | `/` | `LayoutDashboard` | 新（替换 Home 内容） |
| 2 | 持仓决策 | `/holdings` | `ClipboardList` | 新 |
| 3 | 机会清单 | `/opportunities` | `ListChecks` | 新 |
| 4 | 逻辑链 | `/logic-chain` | `Share2` | 新 |
| 5 | Agent | `/agent` | `Bot` | 既有 |
| 6 | 人形机器人 | `/humanoid` | `Bot`/`Cpu` | 新 |
| 7 | AI算力 | `/ai-compute` | `Cpu`/`Zap` | 新 |
| 8 | Serenity 方法论 | `/serenity` | `Compass` | 新 |
| 9 | 事件概率 | `/events` | `Activity` | 新 |
| 10 | 新闻 | `/news` | `Newspaper` | 新 |
| 11 | Alpha Zoo | `/alpha-zoo` | `Layers` | 既有 |
| 12 | Settings | `/settings` | `Settings` | 既有 |
| 13 | Correlation Matrix | `/correlation` | `Grid3x3` | 既有 |

- 侧栏标题维持「Vibe-Trading」。Sessions 列表、明暗切换、折叠逻辑保持不变。

### 3.2 路由
在 `router.tsx` 新增懒加载页面与路由：`/holdings`、`/opportunities`、`/logic-chain`、`/humanoid`、`/ai-compute`、`/serenity`、`/events`、`/news`。Home (`/`) 指向新的市场总览页。

为生产模式/直接访问可用，需要在 `vite.config.ts` 的代理里为这些**前端路由**配置 `html fallback`（参考现有 `/correlation` 的 `apiProxyWithHtmlFallback` 做法），避免刷新 404。

### 3.3 数据层（前端）
新增 `frontend/src/data/` 种子数据模块（TypeScript，纯静态、可类型化）：
- `marketSeed.ts`：大盘指数 + 两组核心标的（含名称、代码、标签、现价、涨跌幅、PE、市值）。值取自图1，作为兜底与初始渲染。
- `humanoidSeed.ts`：人形机器人产业链各 Tab 内容 + 估值全景表（图3 字段：标的/代码/模块/现价/PE(TTM)/PB/总市值/Q1增速/PEG/演化时间/星级/不可替代性/评级）。
- `aiComputeSeed.ts`：AI算力产业链各 Tab 内容 + 核心四标的横向对比表（图2 字段：股价/总市值/PEG/消化时间/核心逻辑）。
- `logicChainSeed.ts`：逻辑链预设（图4 顶部 13 条链）+ 默认节点/连线。
- `holdingsSeed.ts`、`opportunitiesSeed.ts`、`serenitySeed.ts`、`eventsSeed.ts`、`newsSeed.ts`：对应页面的初始内容。

涨跌颜色统一用一个小工具：`frontend/src/lib/cn-market.ts`，导出 `changeColor(v)`（v≥0 → 红 `text-danger`，v<0 → 绿 `text-success`）与格式化函数，集中处理「红涨绿跌」。

### 3.4 市场总览实时行情（前端 + 后端）
- 后端：在 `agent/api_server.py` 新增 `GET /market/overview`（或新建 `agent/src/api/market_routes.py` 并注册），用 Python（`httpx`/`requests`）请求腾讯行情 `https://qt.gtimg.cn/q=<codes>`，按 GBK 解码、解析为 JSON 返回。代码映射：
  - 指数：上证 `sh000001`、深成 `sz399001`、创业 `sz399006`、沪深300 `sh000300`、道琼斯 `usDJI`、纳斯达克 `usIXIC`、标普500 `usINX`。
  - 人形机器人核心标的与 AI 算力核心标的的 6+6 只（精确代码在实现期落定，例：中际旭创 `sz300308`、寒武纪 `sh688256`、绿的谐波 `sh688017`…）。
  - 该端点为只读公开行情、无需鉴权（与 `/health`、`/skills`、`/correlation` 同级，免 `require_auth`）。
- 前端：`frontend/src/hooks/useMarketOverview.ts`，30s 轮询 `/market/overview`，失败/超时回退 `marketSeed.ts`；页面显示「更新时间 + 数据来自腾讯财经公开行情」与手动「刷新」按钮。
- 代理：把 `/market` 加入 `vite.config.ts` 的 `PROXY_PATHS`。

### 3.5 逻辑链交互
图4 需要：拖拽节点、连线、双击编辑文字、Del 删除、4 类彩色节点、缩放。建议引入 `@xyflow/react`（React Flow）作为新依赖，开箱即得这些能力；自定义 4 种节点样式与颜色（触发因素=红、传导逻辑=黄、受益板块=紫、具体标的=绿）。顶部链选择 chips 切换不同预设图；编辑结果存 localStorage。

> 备选：不引依赖、用自写 SVG 画板。但要复刻拖拽/连线成本高，推荐用 React Flow。

---

## 4. 9 个页面逐页设计

复用统一的页面骨架组件：`PageHeader`（标题 + 副标题/元信息 + 右上操作按钮）、`Card`、`DataTable`、`Tabs`、`StatCard`、`Badge`，放在 `frontend/src/components/dashboard/`。所有颜色走语义 token，自动适配明暗。

1. **市场总览（`/`，替换 Home）** — 图1。顶部标题「市场总览」+ 副标题「A股大盘·人形机器人 & AI算力 核心标的、实时行情（腾讯, 30s 自动刷新）」+ 右上「刷新」。区块：① 大盘指数 7 张卡片（指数名 + 点位 + 涨跌幅，红涨绿跌）；② 两栏核心标的表（人形机器人·核心标的 / AI算力·核心标的），列：名称(+标签)/现价/涨跌/PE/市值；底部更新时间与数据来源声明。数据走 `useMarketOverview`。

2. **持仓决策（`/holdings`）** — 截图未展开，按命名实现：当前持仓表（标的/成本/现价/盈亏/仓位）+ 决策建议卡（加/减/持，附理由）。种子数据：以「绿的谐波」为现有持仓示例。

3. **机会清单（`/opportunities`）** — 候选标的清单：标的/板块/触发逻辑/目标价/评分/状态（关注/待买/已买），可按板块筛选。种子数据来自人形机器人/AI算力两组核心标的的「未持仓·等回调」项。

4. **逻辑链（`/logic-chain`）** — 图4。顶部 13 条预设链 chips + 「新建链」；工具栏：添加节点（4 类彩色按钮）/删除选中 + 操作提示；主体 React Flow 画板，含图例与缩放控件；编辑持久化到 localStorage。

5. **人形机器人（`/humanoid`）** — 图3。标题「人形机器人 产业链深度分析」+ 副标题（研报数/覆盖标的/数据日期/市场数据时间）+「刷新行情」。Tabs：总览、成本构成、减速器、丝杠、电机、传感器、腱绳/新材料、替代风险、估值全景、宇树科技。重点实现「估值全景」表（图3 全字段，含星级/标签/评级着色）；其余 Tab 用种子结构化内容渲染。

6. **AI算力（`/ai-compute`）** — 图2。标题「AI算力产业链深度分析」+ 副标题（更新日期/层级环节/标的数/L1评分/数据来源）。Tabs：总览、光模块、PCB/HDI、HBM/存储、长鑫·IPO、CPU/GPU、下游企业、算力能源、太空算力、核心标的、估值全景、AI新闻。重点实现「核心四标的横向对比」表（维度：股价/总市值/PEG/消化时间/核心逻辑）。

7. **Serenity 方法论（`/serenity`）** — 截图未展开，按命名实现：方法论说明页（投资原则/检查清单/纪律），Markdown 风格分节卡片，种子内容可后续编辑。

8. **事件概率（`/events`）** — 事件驱动概率表：事件/发生概率/影响标的/方向/赔率，可加进度条/概率条展示。种子数据若干宏观/产业事件。

9. **新闻（`/news`）** — 新闻流：来源/时间/标题/摘要/关联标的标签，按时间倒序。种子数据若干条；预留后续接 `web_search`/RSS。

---

## 5. 错误处理与回退

- 市场总览：`/market/overview` 失败 → 用种子数据并显示「行情源暂不可用，显示缓存示例数据」提示，不阻塞页面。
- 后端腾讯源异常（超时/格式变化）：后端捕获并返回 200 + `{stale:true}` 或 5xx；前端两种都回退种子。
- React Flow 未安装时：逻辑链页给出降级静态预览（防止构建失败）。
- 所有新页面包裹在现有 `ErrorBoundary` 行为下（路由级 Suspense 已有）。

---

## 6. 测试与验收

- `cd frontend && npm install`（新增 `@xyflow/react`）后 `npm run build` 通过（`tsc -b` 无类型错误）。
- 现有 `vitest` 套件保持绿色；为新增纯函数（`cn-market.ts` 颜色/格式化、行情解析）补单测。
- `npm run dev` 启动，逐页目视对照 4 张截图（明暗两套主题切换都正常）。
- 市场总览在后端运行时显示真实行情并 30s 刷新；后端关闭时回退种子数据且有提示。
- 既有页面（Agent / Alpha Zoo / Settings / Correlation）功能不回归。

---

## 7. 交付范围小结

一次性交付：13 项侧栏 + 9 个新页面（全部）+ 市场总览实时行情（后端 `/market/overview` + 30s 轮询 + 兜底）+ 逻辑链可编辑画板 + 复用骨架组件 + 种子数据模块 + 必要单测 + 构建通过。截图未展开的页面（持仓决策/Serenity/事件概率/新闻）按命名与布局实现到「结构完整、种子内容可用」的程度。
