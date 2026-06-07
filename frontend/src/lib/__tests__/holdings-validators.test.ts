import { describe, expect, it } from "vitest";
import { isValidStockCode, PLACEHOLDER_STOCK_CODE, sanitizeHoldings } from "@/lib/holdings-validators";

describe("holdings-validators", () => {
  it("rejects placeholder code only", () => {
    expect(isValidStockCode(PLACEHOLDER_STOCK_CODE)).toBe(false);
    expect(isValidStockCode("")).toBe(false);
    expect(isValidStockCode("688017")).toBe(true);
  });

  it("does not reject valid codes with zero-like suffix", () => {
    expect(isValidStockCode("000001")).toBe(true);
  });

  it("sanitizeHoldings keeps rows with zero cost/position when code is valid", () => {
    const out = sanitizeHoldings([
      { code: "000000", cost: 0, position: 0 },
      { code: "688017", cost: 0, position: 0 },
    ]);
    expect(out).toHaveLength(1);
    expect(out[0].code).toBe("688017");
  });
});
