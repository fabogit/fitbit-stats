import { KpiGrid } from "../KpiGrid";
import { useAppSelector } from "@/store/store";
import { NoDataState } from "../NoDataState";

export function OverviewView({ onAction }: { onAction?: () => void }) {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  if (filteredData.length === 0) {
    return (
      <NoDataState 
        onAction={onAction} 
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Health Overview
        </h2>
        <p className="text-muted-foreground">
          Key metrics summary for the selected period.
        </p>
      </div>

      <KpiGrid />
    </div>
  );
}
