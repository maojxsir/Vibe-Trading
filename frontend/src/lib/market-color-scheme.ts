import { loadPersisted, savePersisted } from "./persist";

/** User preference for up/down colors in charts and quote tables. */
export type MarketColorScheme = "auto" | "cn" | "us";

const STORAGE_KEY = "market-color-scheme";
export const MARKET_COLOR_SCHEME_EVENT = "vt-market-color-scheme";

export function getMarketColorScheme(): MarketColorScheme {
  const raw = loadPersisted<string>(STORAGE_KEY, "auto");
  if (raw === "cn" || raw === "us" || raw === "auto") return raw;
  return "auto";
}

export function setMarketColorScheme(scheme: MarketColorScheme): void {
  savePersisted(STORAGE_KEY, scheme);
  window.dispatchEvent(new CustomEvent(MARKET_COLOR_SCHEME_EVENT, { detail: scheme }));
}

function isChineseLocale(): boolean {
  return (document.documentElement.lang || navigator.language || "").startsWith("zh");
}

/** Resolve whether up moves should use CN convention (red up, green down). */
export function isCnColorScheme(scheme: MarketColorScheme = getMarketColorScheme()): boolean {
  if (scheme === "cn") return true;
  if (scheme === "us") return false;
  return isChineseLocale();
}

export function changeColorClassForChange(change: number, cn = isCnColorScheme()): string {
  const upClass = cn ? "text-danger" : "text-success";
  const downClass = cn ? "text-success" : "text-danger";
  return change >= 0 ? upClass : downClass;
}

export const MARKET_COLOR_SCHEME_OPTIONS: {
  value: MarketColorScheme;
  label: string;
  description: string;
}[] = [
  {
    value: "auto",
    label: "Auto (browser locale)",
    description: "Chinese locale → red up / green down; otherwise green up / red down.",
  },
  {
    value: "cn",
    label: "China A-share (红涨绿跌)",
    description: "Red for up / positive, green for down / negative.",
  },
  {
    value: "us",
    label: "US / Western (绿涨红跌)",
    description: "Green for up / positive, red for down / negative.",
  },
];
