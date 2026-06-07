import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { StockChartDrawer } from "@/components/market/StockChartDrawer";

export interface StockChartTarget {
  code: string;
  name: string;
}

interface StockChartDrawerContextValue {
  open: (target: StockChartTarget) => void;
  close: () => void;
}

const StockChartDrawerContext = createContext<StockChartDrawerContextValue | null>(null);

export function StockChartDrawerProvider({ children }: { children: ReactNode }) {
  const [target, setTarget] = useState<StockChartTarget | null>(null);
  const open = useCallback((next: StockChartTarget) => setTarget(next), []);
  const close = useCallback(() => setTarget(null), []);

  return (
    <StockChartDrawerContext.Provider value={{ open, close }}>
      {children}
      <StockChartDrawer target={target} onClose={close} />
    </StockChartDrawerContext.Provider>
  );
}

export function useStockChartDrawer(): StockChartDrawerContextValue {
  const ctx = useContext(StockChartDrawerContext);
  if (!ctx) {
    throw new Error("useStockChartDrawer must be used within StockChartDrawerProvider");
  }
  return ctx;
}
