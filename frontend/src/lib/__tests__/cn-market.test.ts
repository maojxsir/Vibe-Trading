import { describe, it, expect } from "vitest";
import { changeColorClass, fmtPct, fmtPrice, fmtMarketCap } from "@/lib/cn-market";

describe("cn-market", () => {
  it("红涨绿跌: >=0 红, <0 绿", () => {
    expect(changeColorClass(2.9)).toBe("text-danger");
    expect(changeColorClass(0)).toBe("text-danger");
    expect(changeColorClass(-0.2)).toBe("text-success");
  });

  it("百分比带符号, 两位小数", () => {
    expect(fmtPct(2.9)).toBe("+2.90%");
    expect(fmtPct(-0.2)).toBe("-0.20%");
    expect(fmtPct(0)).toBe("+0.00%");
  });

  it("价格两位小数", () => {
    expect(fmtPrice(314.88)).toBe("314.88");
    expect(fmtPrice(40)).toBe("40.00");
  });

  it("市值: 万亿换算", () => {
    expect(fmtMarketCap(577)).toBe("577");
    expect(fmtMarketCap(14148)).toBe("1.41万亿");
  });
});
