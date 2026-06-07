import type { Holding } from "@/data/holdingsSeed";
import { isValidImportedHolding, isValidStockCode } from "@/lib/holdings-validators";

export interface ImportedHolding {
  code: string;
  name: string;
  cost?: number | null;
  position?: number | null;
  shares?: number | null;
  confidence?: number;
  warnings?: string[];
}

export function mergeHoldings(existing: Holding[], imported: ImportedHolding[]): Holding[] {
  const out = existing.map((holding) => ({ ...holding }));

  for (const row of imported) {
    const code = String(row.code || "").trim();
    if (!isValidImportedHolding({ code })) continue;
    const idx = out.findIndex((holding) => holding.code === code);
    if (idx >= 0) {
      const current = out[idx];
      out[idx] = {
        ...current,
        name: row.name || current.name,
        cost: row.cost ?? current.cost,
        position: row.position ?? current.position,
      };
    } else {
      out.push({
        name: row.name || code,
        code,
        cost: row.cost ?? 0,
        price: 0,
        position: row.position ?? 0,
        action: null,
        reason: "",
      });
    }
  }

  return out.filter((holding) => isValidStockCode(holding.code));
}
