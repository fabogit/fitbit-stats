import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppDispatch, useAppSelector } from "../../store/store";
import { fetchHealthData } from "../../features/dashboard/dashboardSlice";

interface DataErrorStateProps {
  onRecalculate: () => void;
}

/** Shown when the dashboard data exists but could not be loaded (not the empty state). */
export function DataErrorState({ onRecalculate }: DataErrorStateProps) {
  const dispatch = useAppDispatch();
  const error = useAppSelector((state) => state.dashboard.error);

  return (
    <div
      role="alert"
      data-testid="data-error-state"
      className="flex flex-col items-center justify-center p-12 text-center bg-card/50 border border-destructive/40 rounded-3xl max-w-2xl mx-auto my-12"
    >
      <AlertTriangle className="w-12 h-12 text-destructive mb-4" />
      <h3 className="text-2xl font-extrabold tracking-tight mb-2">Could not load your data</h3>
      <p className="text-muted-foreground mb-6 break-words max-w-full">
        {error || "Unknown error"}
      </p>
      <div className="flex flex-wrap gap-3 justify-center">
        <Button onClick={() => dispatch(fetchHealthData({ force: true }))}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Try again
        </Button>
        <Button variant="outline" onClick={onRecalculate}>
          Recalculate
        </Button>
      </div>
    </div>
  );
}
