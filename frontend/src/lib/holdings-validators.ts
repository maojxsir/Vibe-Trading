const A_SHARE_CODE = /^\d{6}$/;

/** Placeholder / draft symbol from "添加持仓" — not a real A-share listing. */
export const PLACEHOLDER_STOCK_CODE = "000000";

/** Valid listing code for persistence/import. Cost or position may be 0. */
export function isValidStockCode(code: string): boolean {
  const trimmed = String(code || "").trim();
  return A_SHARE_CODE.test(trimmed) && trimmed !== PLACEHOLDER_STOCK_CODE;
}

export function isValidImportedHolding(row: { code: string }): boolean {
  return isValidStockCode(row.code);
}

/** Drop only rows with missing or placeholder codes; keep cost/position/shares at 0. */
export function sanitizeHoldings<T extends { code: string }>(rows: T[]): T[] {
  return rows.filter((row) => isValidStockCode(row.code));
}
