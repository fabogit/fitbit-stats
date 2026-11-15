import { Loader2 } from "lucide-react";
import { useAppSelector } from "../../store/store";

/** Compact ETL progress shown above any view while a recalculation is running. */
export function EtlProgressBanner() {
  const { isProcessing, etlProgress, etlStep } = useAppSelector((state) => state.dashboard);

  if (!isProcessing) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="etl-progress-banner"
      className="sticky top-0 z-30 border-b border-border bg-card/95 backdrop-blur px-4 md:px-8 py-3"
    >
      <div className="flex items-center gap-3 mb-2">
        <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
        <span className="text-sm font-semibold">Recalculating</span>
        <span className="text-sm text-muted-foreground truncate flex-1">
          {etlStep || "Initializing..."}
        </span>
        <span className="text-sm font-bold text-primary tabular-nums">{etlProgress}%</span>
      </div>
      <div className="h-1.5 w-full bg-muted/50 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${etlProgress}%` }}
        />
      </div>
    </div>
  );
}
