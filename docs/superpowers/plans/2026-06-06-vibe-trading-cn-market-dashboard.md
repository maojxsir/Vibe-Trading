# A股投研工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Vibe-Trading 前端改造成 4 张截图所示的 A 股投研工作台：13 项侧栏 + 9 个新页面 + 市场总览实时行情（含兜底）+ 可编辑逻辑链，且不破坏现有后端/页面。

**Architecture:** 纯增量改造。新增 `frontend/src/data/`（种子数据）、`frontend/src/components/dashboard/`（骨架组件）、`frontend/src/pages/` 下 9 个页面、`frontend/src/hooks/useMarketOverview.ts`、`frontend/src/lib/cn-market.ts`；后端新增只读 `GET /market/overview` 腾讯行情代理；改 `Layout.tsx` 的 `NAV`、`router.tsx`、`vite.config.ts` 代理。涨跌色「红涨绿跌」集中在 `cn-market.ts`。明暗复用现有主题。

**Tech Stack:** React 19, react-router-dom 7, TypeScript, Tailwind 3.4（语义 token）, ECharts 6, lucide-react, zustand, vitest；新增 `@xyflow/react`（逻辑链）；后端 FastAPI + httpx。

---

## File Structure

新建：
- `frontend/src/lib/cn-market.ts` — 涨跌色/格式化工具（纯函数，可测）。
- `frontend/src/data/types.ts` — 种子数据类型。
- `frontend/src/data/marketSeed.ts` / `humanoidSeed.ts` / `aiComputeSeed.ts` / `logicChainSeed.ts` / `holdingsSeed.ts` / `opportunitiesSeed.ts` / `serenitySeed.ts` / `eventsSeed.ts` / `newsSeed.ts`
- `frontend/src/components/dashboard/PageHeader.tsx` / `Card.tsx` / `DataTable.tsx` / `Tabs.tsx` / `StatCard.tsx` / `Badge.tsx`
- `frontend/src/hooks/useMarketOverview.ts`
- `frontend/src/pages/MarketOverview.tsx`（替换 Home 内容）/ `Holdings.tsx` / `Opportunities.tsx` / `LogicChain.tsx` / `Humanoid.tsx` / `AICompute.tsx` / `Serenity.tsx` / `Events.tsx` / `News.tsx`
- `agent/src/api/market_routes.py` — 腾讯行情解析 + 路由。
- `agent/tests/test_market_routes.py` — 解析单测。
- `frontend/src/lib/__tests__/cn-market.test.ts`

修改：
- `frontend/src/components/layout/Layout.tsx`（`NAV`）
- `frontend/src/router.tsx`（新路由）
- `frontend/src/lib/api.ts`（加 `getMarketOverview`）
- `frontend/vite.config.ts`（`/market` 代理 + 新页面 html fallback）
- `agent/api_server.py`（注册 market 路由）
- `frontend/package.json`（`@xyflow/react`）

---

### Task 1: 颜色/格式化工具 cn-market（TDD）

**Files:** Create `frontend/src/lib/cn-market.ts`; Test `frontend/src/lib/__tests__/cn-market.test.ts`

- [ ] Step 1: 写失败测试（changeColorClass/fmtPct/fmtPrice，红涨绿跌）。
- [ ] Step 2: `npx vitest run src/lib/__tests__/cn-market.test.ts` 确认 FAIL。
- [ ] Step 3: 实现（change>=0 → text-danger，<0 → text-success；fmtPct 带符号两位；fmtPrice 两位）。
- [ ] Step 4: 确认 PASS。
- [ ] Step 5: commit `feat(fe): cn-market color/format helpers (red up, green down)`

### Task 2: 种子数据类型 + marketSeed
**Files:** Create `frontend/src/data/types.ts`, `marketSeed.ts`
- [ ] 定义 IndexQuote/StockQuote/MarketOverview；marketSeed 用图1 数值（指数7 + 人形6 + AI6）。
- [ ] commit `feat(fe): market overview types + seed data`

### Task 3: 后端 /market/overview 腾讯行情代理（TDD 解析）
**Files:** Create `agent/src/api/market_routes.py`, `agent/tests/test_market_routes.py`; Modify `agent/api_server.py`
- [ ] parse_tencent_line 单测（name/price/change_pct）→ FAIL → 实现 → PASS。
- [ ] include_router，无鉴权（公开行情），异常返回 stale。
- [ ] commit `feat(api): /market/overview tencent quote proxy`

### Task 4: 骨架组件 + 导航 + 路由 + 代理
**Files:** Create `components/dashboard/{PageHeader,Card,DataTable,Tabs,StatCard,Badge}.tsx`; Modify Layout.tsx(NAV 13项), router.tsx, vite.config.ts, lib/api.ts
- [ ] 骨架组件用语义 token；NAV 13 项按截图顺序/图标；新路由；/market 代理 + html fallback；getMarketOverview。
- [ ] `npm run build` 通过（先空壳占位）。
- [ ] commit `feat(fe): dashboard primitives, 13-item nav, routes, market proxy`

### Task 5: 市场总览页（图1）+ useMarketOverview
- [ ] hook 30s 轮询 + 失败兜底 seed(stale)；页面按图1（大盘指数7卡 + 两栏核心标的表 + 来源声明 + 刷新）。
- [ ] build 通过；commit `feat(fe): market overview page with 30s live quotes + seed fallback`

### Task 6: AI算力页（图2）
- [ ] aiComputeSeed（12 Tab + 核心四标的横向对比 PEG/消化时间/核心逻辑）；AICompute.tsx Tabs + 总览表。
- [ ] commit `feat(fe): AI compute industry-chain page`

### Task 7: 人形机器人页（图3）
- [ ] humanoidSeed（10 Tab + 估值全景全字段）；Humanoid.tsx Tabs + 估值全景 DataTable（着色/星级/Badge）。
- [ ] commit `feat(fe): humanoid robot industry-chain page`

### Task 8: 逻辑链页（图4，React Flow）
- [ ] `npm i @xyflow/react`；logicChainSeed（13 链 + 默认节点/连线，4 类彩色节点）；LogicChain.tsx 画板+工具栏+图例+localStorage；降级静态列表。
- [ ] commit `feat(fe): editable logic-chain graph (react-flow)`

### Task 9: 其余 5 页（持仓决策/机会清单/Serenity/事件概率/新闻）
- [ ] 各页 + seed：持仓表+决策卡；机会清单候选表；Serenity 分节卡；事件概率表+概率条；新闻流。
- [ ] commit `feat(fe): holdings/opportunities/serenity/events/news pages`

### Task 10: 收尾验收
- [ ] frontend `npm run build` 通过；`npx vitest run` 全绿；agent pytest 通过；`npm run dev` 逐页对照截图；既有页不回归。
- [ ] commit `chore: build/test green for dashboard transformation`

---

## Self-Review
- Spec coverage: 侧栏(T4)/9页(T5-9)/实时行情+兜底(T3-5)/红涨绿跌(T1)/逻辑链(T8)/明暗复用(全程语义token)/测试构建(T10) 均覆盖。✔
- Placeholder scan: 无 TBD/TODO。✔
- Type consistency: MarketOverview/StockQuote/IndexQuote(T2)；后端 name/price/change_pct(T3) → hook changePct(T5)；changeColorClass/fmtPct/fmtPrice 全程一致。✔
