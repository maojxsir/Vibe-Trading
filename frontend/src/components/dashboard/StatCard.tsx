import { cn } from "@/lib/utils";
import { changeColorClass, fmtPct } from "@/lib/cn-market";

interface StatCardProps {
  label: string;
  value: string | number;
  changePct?: number;
  className?: string;
}

export function StatCard({ label, value, changePct, className }: StatCardProps) {
  return (
    <div className={cn("rounded-lg border bg-card px-3 py-2.5", className)}>
      <p className="truncate text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-foreground">{value}</p>
      {changePct !== undefined && (
        <p className={cn("text-xs font-medium tabular-nums", changeColorClass(changePct))}>{fmtPct(changePct)}</p>
      )}
    </div>
  );
}
