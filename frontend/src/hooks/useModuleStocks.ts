import { useCallback, useState } from "react";
import type { ModuleStock } from "@/data/types";
import { api } from "@/lib/api";
import { loadPersisted, savePersisted } from "@/lib/persist";

export function useModuleStocks(persistKey: string, seed: Record<string, ModuleStock[]>) {
  const [moduleStocks, setModuleStocks] = useState<Record<string, ModuleStock[]>>(() =>
    loadPersisted(persistKey, seed),
  );
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<Record<string, string>>(() =>
    loadPersisted(`${persistKey}:meta`, {}),
  );

  const refreshModule = useCallback(
    async (theme: string, module: string) => {
      setGenerating(true);
      setGenError(null);
      try {
        const wire = await api.generateModuleStocks(theme, module);
        if (wire.error) {
          throw new Error(wire.error);
        }
        if (!wire.stocks?.length) {
          throw new Error("Agent 未返回有效标的");
        }
        setModuleStocks((prev) => {
          const next = { ...prev, [module]: wire.stocks };
          savePersisted(persistKey, next);
          return next;
        });
        const ts = new Date().toISOString();
        setRefreshedAt((prev) => {
          const next = { ...prev, [module]: ts };
          savePersisted(`${persistKey}:meta`, next);
          return next;
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "生成失败";
        setGenError(`${msg}（需后端运行且已配置 LLM key）`);
      } finally {
        setGenerating(false);
      }
    },
    [persistKey],
  );

  const resetModule = useCallback(
    (module: string) => {
      setGenError(null);
      setModuleStocks((prev) => {
        const next = { ...prev, [module]: seed[module] ?? [] };
        savePersisted(persistKey, next);
        return next;
      });
      setRefreshedAt((prev) => {
        const next = { ...prev };
        delete next[module];
        savePersisted(`${persistKey}:meta`, next);
        return next;
      });
    },
    [persistKey, seed],
  );

  return { moduleStocks, refreshModule, resetModule, generating, genError, refreshedAt };
}
