import { describe, expect, it } from "vitest";
import { mergeHoldings } from "@/lib/holdings-merge";
import type { Holding } from "@/data/holdingsSeed";

const base = (patch: Partial<Holding>): Holding => ({
  name: "A",
  code: "000001",
  cost: 1,
  price: 0,
  position: 10,
  action: "持有",
  reason: "",
  ...patch,
});

describe("mergeHoldings", () => {
  it("updates by code and appends new rows", () => {
    const out = mergeHoldings(
      [base({ code: "000001", name: "A", cost: 1, position: 10 })],
      [
        { code: "000001", name: "A", cost: 2, position: 20 },
        { code: "000002", name: "B", cost: 3, position: 5 },
      ],
    );

    expect(out).toHaveLength(2);
    expect(out[0].cost).toBe(2);
    expect(out[0].position).toBe(20);
    expect(out[1]).toMatchObject({ code: "000002", name: "B", action: null });
  });

  it("preserves existing rows that are not imported", () => {
    const out = mergeHoldings(
      [base({ code: "000001" }), base({ code: "000003", reason: "keep me" })],
      [{ code: "000001", name: "A", cost: 2, position: 10 }],
    );

    expect(out).toHaveLength(2);
    expect(out[1]).toMatchObject({ code: "000003", reason: "keep me" });
  });

  it("does not overwrite an existing position with an empty imported position", () => {
    const out = mergeHoldings(
      [base({ code: "000001", position: 30 })],
      [{ code: "000001", name: "A", cost: 2, position: null }],
    );

    expect(out[0].position).toBe(30);
  });

  it("skips placeholder and invalid imported codes", () => {
    const out = mergeHoldings(
      [base({ code: "000001" })],
      [
        { code: "000000", name: "新标的", cost: 0, position: 0 },
        { code: "000002", name: "B", cost: 3, position: 5 },
      ],
    );

    expect(out).toHaveLength(2);
    expect(out.some((row) => row.code === "000000")).toBe(false);
    expect(out[1]).toMatchObject({ code: "000002", name: "B" });
  });

  it("keeps valid codes when cost and position are zero", () => {
    const out = mergeHoldings([], [{ code: "688017", name: "绿的谐波", cost: 0, position: 0 }]);

    expect(out).toHaveLength(1);
    expect(out[0]).toMatchObject({ code: "688017", cost: 0, position: 0 });
  });
});
