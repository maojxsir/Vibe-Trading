import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { ChevronsUpDown, Loader2, Search } from "lucide-react";
import { useSymbolSearch } from "@/hooks/useSymbolSearch";
import type { SymbolSearchResultWire } from "@/lib/api";
import { cn } from "@/lib/utils";

interface StockSymbolComboboxProps {
  value: { name: string; code: string };
  onSelect: (symbol: SymbolSearchResultWire) => void;
  boostCodes?: string[];
  className?: string;
}

export function StockSymbolCombobox({ value, onSelect, boostCodes = [], className }: StockSymbolComboboxProps) {
  const id = useId();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(() => (value.code === "000000" ? "" : `${value.name} ${value.code}`));
  const [active, setActive] = useState(0);
  const { results, loading, error } = useSymbolSearch(query, boostCodes);

  useEffect(() => {
    if (!open) {
      setQuery(value.code === "000000" ? "" : `${value.name} ${value.code}`);
    }
  }, [open, value.code, value.name]);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  useEffect(() => setActive(0), [query, results.length]);

  const select = (symbol: SymbolSearchResultWire) => {
    onSelect(symbol);
    setQuery(`${symbol.name} ${symbol.code}`);
    setOpen(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!open && ["ArrowDown", "ArrowUp"].includes(event.key)) {
      setOpen(true);
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((idx) => Math.min(idx + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((idx) => Math.max(idx - 1, 0));
    } else if (event.key === "Enter" && open && results[active]) {
      event.preventDefault();
      select(results[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={rootRef} className={cn("relative min-w-[180px]", className)}>
      <div className="flex items-center rounded-md border bg-background px-2 py-1 shadow-sm focus-within:border-primary">
        <Search className="mr-1.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-listbox`}
          value={query}
          onFocus={() => {
            setOpen(true);
            if (value.code === "000000") setQuery("");
          }}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onKeyDown={onKeyDown}
          placeholder="代码 / 名称 / 拼音"
          className="min-w-0 flex-1 bg-transparent text-xs outline-none placeholder:text-muted-foreground"
        />
        {loading ? (
          <Loader2 className="ml-1 h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
        ) : (
          <ChevronsUpDown className="ml-1 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
      </div>

      {open && (
        <div
          id={`${id}-listbox`}
          role="listbox"
          className="absolute left-0 top-full z-40 mt-1 max-h-64 w-full min-w-[240px] overflow-y-auto rounded-md border bg-card p-1 text-xs shadow-lg"
        >
          {error ? (
            <div className="px-2 py-2 text-warning">{error}</div>
          ) : results.length === 0 && !loading ? (
            <div className="px-2 py-2 text-muted-foreground">未找到匹配标的</div>
          ) : (
            results.map((symbol, idx) => (
              <button
                key={symbol.code}
                type="button"
                role="option"
                aria-selected={idx === active}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => select(symbol)}
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded px-2 py-2 text-left hover:bg-muted",
                  idx === active && "bg-muted",
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium text-foreground">{symbol.name}</span>
                  <span className="block text-[11px] text-muted-foreground">{symbol.cnspell || symbol.ts_code}</span>
                </span>
                <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{symbol.code}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
