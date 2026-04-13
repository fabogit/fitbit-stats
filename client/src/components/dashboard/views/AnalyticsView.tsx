import { useAppSelector } from "@/store/store";
import { NoDataState } from "../NoDataState";
import { ZonesChart } from "../charts/ZonesChart";
import { ScatterChart } from "../charts/ScatterChart";
import { WeeklyChart } from "../charts/WeeklyChart";
import { ActivityHeatmap } from "../charts/ActivityHeatmap";
import { RHRCorrelationChart } from "../charts/RHRCorrelationChart";
import { SedentaryTrendChart } from "../charts/SedentaryTrendChart";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { cn } from "@/lib/utils";

export function AnalyticsView({ onAction }: { onAction?: () => void }) {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const isMobile = useMediaQuery("(max-width: 640px)");

  if (filteredData.length === 0) {
    return <NoDataState onAction={onAction} />;
  }

  const chartHeight = isMobile ? "h-[300px]" : "h-[380px]";

  return (
    <div className="space-y-6 md:space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10 max-w-7xl mx-auto">
      {/* 1. Heatmap (Full Width) */}
      <ActivityHeatmap />

      {/* 2. Grid for Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-10">
        <div className={cn("lg:col-span-1", chartHeight)}>
          <ZonesChart />
        </div>
        <div className={cn("lg:col-span-1", chartHeight)}>
          <WeeklyChart />
        </div>

        <div className="lg:col-span-2 h-[350px] md:h-[400px]">
          <ScatterChart />
        </div>
        <div className="lg:col-span-2 h-[350px] md:h-[400px]">
          <RHRCorrelationChart />
        </div>

        <div className="lg:col-span-2 h-[350px] md:h-[400px]">
          <SedentaryTrendChart />
        </div>

      </div>
    </div>
  );
}
