// China A-share market display helpers.
//
// IMPORTANT: A-share convention is the opposite of the repo default and of
// Western markets: red = up/positive, green = down/negative. All CN-market
// pages funnel their colour decisions through here so the convention stays
// consistent in one place.

export function changeColorClass(change: number): string {
  return change >= 0 ? "text-danger" : "text-success";
}

export function fmtPct(pct: number): string {
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export function fmtPrice(price: number): string {
  return price.toFixed(2);
}

// Market cap is supplied in 亿 (100M CNY). Keep it compact for table cells.
export function fmtMarketCap(yi: number): string {
  if (yi >= 10000) return `${(yi / 10000).toFixed(2)}万亿`;
  return `${yi.toLocaleString("en-US")}`;
}

// Normalize a bare A-share code (e.g. "688017", "300308", "002472") to the
// exchange-prefixed form Tencent expects ("sh688017", "sz300308", ...).
// Already-prefixed codes (sh/sz/bj/us) are returned unchanged.
export function toTencentCode(code: string): string {
  const c = code.trim();
  if (/^(sh|sz|bj|us)/i.test(c)) return c;
  const num = c.split(".")[0];
  if (/^(60|68|11|51|58|90)/.test(num)) return `sh${num}`;
  if (/^(00|30|12|15|16|18|20|39)/.test(num)) return `sz${num}`;
  if (/^(8|4|92)/.test(num)) return `bj${num}`;
  return `sh${num}`;
}
