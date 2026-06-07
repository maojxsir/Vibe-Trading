import { describe, it, expect, beforeEach } from "vitest";
import {
  changeColorClassForChange,
  getMarketColorScheme,
  isCnColorScheme,
  setMarketColorScheme,
} from "@/lib/market-color-scheme";

describe("market-color-scheme", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to auto", () => {
    expect(getMarketColorScheme()).toBe("auto");
  });

  it("persists user choice", () => {
    setMarketColorScheme("cn");
    expect(getMarketColorScheme()).toBe("cn");
    setMarketColorScheme("us");
    expect(getMarketColorScheme()).toBe("us");
  });

  it("CN scheme: red up, green down", () => {
    expect(changeColorClassForChange(1, true)).toBe("text-danger");
    expect(changeColorClassForChange(0, true)).toBe("text-danger");
    expect(changeColorClassForChange(-1, true)).toBe("text-success");
  });

  it("US scheme: green up, red down", () => {
    expect(changeColorClassForChange(1, false)).toBe("text-success");
    expect(changeColorClassForChange(-1, false)).toBe("text-danger");
  });

  it("isCnColorScheme resolves explicit modes", () => {
    expect(isCnColorScheme("cn")).toBe(true);
    expect(isCnColorScheme("us")).toBe(false);
  });
});
