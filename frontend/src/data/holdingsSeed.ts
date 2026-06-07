// Types for the 持仓决策 (holdings / decision) page.
// Holdings facts (symbol, cost, position) are user-maintained; action/reason come from Agent.

export type DecisionAction = "加仓" | "减仓" | "持有" | "清仓";

export interface Holding {
  name: string;
  code: string;
  cost: number;
  price: number;
  position: number; // % of portfolio
  /** null until Agent review fills a recommendation */
  action: DecisionAction | null;
  reason: string;
}

const LEGACY_DEMO_CODES = ["688017", "300124", "002472"];

/** Detect rows left from the old built-in demo portfolio and drop them on load. */
export function isLegacyDemoHoldings(rows: Holding[]): boolean {
  if (rows.length !== LEGACY_DEMO_CODES.length) return false;
  const codes = rows.map((r) => r.code).sort();
  return codes.every((c, i) => c === [...LEGACY_DEMO_CODES].sort()[i]);
}

export const DECISION_ACTION_TONE: Record<
  DecisionAction,
  "danger" | "success" | "neutral" | "warning"
> = {
  加仓: "danger",
  减仓: "success",
  持有: "neutral",
  清仓: "warning",
};

export function decisionLabel(action: DecisionAction | null): string {
  return action ?? "待建议";
}

export function decisionTone(action: DecisionAction | null): "neutral" | "danger" | "success" | "warning" {
  if (!action) return "neutral";
  return DECISION_ACTION_TONE[action];
}
