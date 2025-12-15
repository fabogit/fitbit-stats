import { ZonesChart } from "../charts/ZonesChart";
import { ScatterChart } from "../charts/ScatterChart";
import { WeeklyChart } from "../charts/WeeklyChart";
import { ActivityHeatmap } from "../charts/ActivityHeatmap";

export function AnalyticsView() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      {/* 1. Heatmap (Full Width) */}
      <ActivityHeatmap />

      {/* 2. Grid for Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="lg:col-span-1">
          <ZonesChart />
        </div>
        <div className="lg:col-span-1">
          <ScatterChart />
        </div>

        <div className="lg:col-span-2">
          <WeeklyChart />
        </div>
      </div>
    </div>
  );
}
