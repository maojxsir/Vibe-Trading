import { Suspense, lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";

const MarketOverview = lazy(() =>
  import("@/pages/MarketOverview").then((m) => ({ default: m.MarketOverview })),
);
const Holdings = lazy(() => import("@/pages/Holdings").then((m) => ({ default: m.Holdings })));
const Opportunities = lazy(() =>
  import("@/pages/Opportunities").then((m) => ({ default: m.Opportunities })),
);
const LogicChain = lazy(() =>
  import("@/pages/LogicChain").then((m) => ({ default: m.LogicChain })),
);
const Humanoid = lazy(() => import("@/pages/Humanoid").then((m) => ({ default: m.Humanoid })));
const AICompute = lazy(() => import("@/pages/AICompute").then((m) => ({ default: m.AICompute })));
const Serenity = lazy(() => import("@/pages/Serenity").then((m) => ({ default: m.Serenity })));
const Events = lazy(() => import("@/pages/Events").then((m) => ({ default: m.Events })));
const News = lazy(() => import("@/pages/News").then((m) => ({ default: m.News })));
const Agent = lazy(() => import("@/pages/Agent").then((m) => ({ default: m.Agent })));
const RunDetail = lazy(() =>
  import("@/pages/RunDetail").then((m) => ({ default: m.RunDetail })),
);
const Compare = lazy(() =>
  import("@/pages/Compare").then((m) => ({ default: m.Compare })),
);
const Settings = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.Settings })),
);
const Correlation = lazy(() =>
  import("@/pages/Correlation").then((m) => ({ default: m.Correlation })),
);
const AlphaZoo = lazy(() =>
  import("@/pages/AlphaZoo").then((m) => ({ default: m.AlphaZoo })),
);

function PageLoader() {
  return (
    <div className="flex h-[60vh] items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
}

function wrap(Component: ComponentType) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: wrap(MarketOverview) },
      { path: "/holdings", element: wrap(Holdings) },
      { path: "/opportunities", element: wrap(Opportunities) },
      { path: "/logic-chain", element: wrap(LogicChain) },
      { path: "/humanoid", element: wrap(Humanoid) },
      { path: "/ai-compute", element: wrap(AICompute) },
      { path: "/serenity", element: wrap(Serenity) },
      { path: "/events", element: wrap(Events) },
      { path: "/news", element: wrap(News) },
      { path: "/agent", element: wrap(Agent) },
      { path: "/settings", element: wrap(Settings) },
      { path: "/runs/:runId", element: wrap(RunDetail) },
      { path: "/compare", element: wrap(Compare) },
      { path: "/correlation", element: wrap(Correlation) },
      { path: "/alpha-zoo", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/bench", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/:alphaId", element: wrap(AlphaZoo) },
    ],
  },
]);
