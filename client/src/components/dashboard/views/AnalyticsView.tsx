import { ZonesChart } from "../charts/ZonesChart";
import { ScatterChart } from "../charts/ScatterChart";
import { WeeklyChart } from "../charts/WeeklyChart";

export function AnalyticsView() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      {/* Row 1: Pie & Scatter */}
      <div className="lg:col-span-1">
        <ZonesChart />
      </div>
      <div className="lg:col-span-1">
        <ScatterChart />
      </div>

      {/* Row 2: Wekly (Full Width) */}
      <div className="lg:col-span-2">
        <WeeklyChart />
      </div>
    </div>
  );
}
