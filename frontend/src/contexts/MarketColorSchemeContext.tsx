import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { invalidateChartThemeCache } from "@/lib/chart-theme";
import {
  MARKET_COLOR_SCHEME_EVENT,
  changeColorClassForChange,
  getMarketColorScheme,
  isCnColorScheme,
  setMarketColorScheme,
  type MarketColorScheme,
} from "@/lib/market-color-scheme";

interface MarketColorSchemeContextValue {
  scheme: MarketColorScheme;
  cn: boolean;
  setScheme: (scheme: MarketColorScheme) => void;
  changeColorClass: (change: number) => string;
}

const MarketColorSchemeContext = createContext<MarketColorSchemeContextValue | null>(null);

export function MarketColorSchemeProvider({ children }: { children: ReactNode }) {
  const [scheme, setSchemeState] = useState<MarketColorScheme>(() => getMarketColorScheme());

  useEffect(() => {
    const onChange = (event: Event) => {
      const next = (event as CustomEvent<MarketColorScheme>).detail ?? getMarketColorScheme();
      setSchemeState(next);
      invalidateChartThemeCache();
    };
    window.addEventListener(MARKET_COLOR_SCHEME_EVENT, onChange);
    return () => window.removeEventListener(MARKET_COLOR_SCHEME_EVENT, onChange);
  }, []);

  const setScheme = useCallback((next: MarketColorScheme) => {
    setMarketColorScheme(next);
    invalidateChartThemeCache();
    setSchemeState(next);
  }, []);

  const cn = isCnColorScheme(scheme);
  const changeColorClass = useCallback((change: number) => changeColorClassForChange(change, cn), [cn]);

  const value = useMemo(
    () => ({ scheme, cn, setScheme, changeColorClass }),
    [scheme, cn, setScheme, changeColorClass],
  );

  return <MarketColorSchemeContext.Provider value={value}>{children}</MarketColorSchemeContext.Provider>;
}

export function useMarketColorScheme(): MarketColorSchemeContextValue {
  const ctx = useContext(MarketColorSchemeContext);
  if (!ctx) {
    throw new Error("useMarketColorScheme must be used within MarketColorSchemeProvider");
  }
  return ctx;
}
