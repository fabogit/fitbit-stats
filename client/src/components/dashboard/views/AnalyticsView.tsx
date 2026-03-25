import { useAppSelector } from "@/store/store";
import { NoDataState } from "../NoDataState";
import { ZonesChart } from "../charts/ZonesChart";
import { ScatterChart } from "../charts/ScatterChart";
import { WeeklyChart } from "../charts/WeeklyChart";
import { ActivityHeatmap } from "../charts/ActivityHeatmap";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { cn } from "@/lib/utils";

export function AnalyticsView({ onAction }: { onAction?: () => void }) {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const isMobile = useMediaQuery("(max-width: 640px)");

  if (filteredData.length === 0) {
    return <NoDataState onAction={onAction} />;
  }

  const chartHeight = isMobile ? "h-[250px]" : "h-[320px]";

  return (
    <div className="space-y-4 md:space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      {/* 1. Heatmap (Full Width) */}
      <ActivityHeatmap />

      {/* 2. Grid for Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <div className={cn("lg:col-span-1", chartHeight)}>
          <ZonesChart />
        </div>
        <div className={cn("lg:col-span-1", chartHeight)}>
          <ScatterChart />
        </div>

        <div className={cn("lg:col-span-2 h-[300px] md:h-[350px]")}>
          <WeeklyChart />
        </div>
      </div>
    </div>
  );
}
