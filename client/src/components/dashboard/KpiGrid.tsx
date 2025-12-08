import type { ReactNode } from "react";
import { useAppSelector } from "@/store";
import {
  calculateAverage,
  formatNumber,
  getLastValidMetric,
} from "@/lib/analytics";
import { TrendingUp, Activity, Moon, Zap } from "lucide-react";

// --- Type Definitions ---
interface KpiCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  colorClass?: string;
}

// --- Main Component ---
export function KpiGrid() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  if (filteredData.length === 0) {
    return (
      <div className="text-slate-500 text-sm">
        No data available for this range.
      </div>
    );
  }

  const avgRHR = calculateAverage(filteredData, "resting_bpm");
  const avgSleep = calculateAverage(filteredData, "overall_score");
  const avgCals = calculateAverage(filteredData, "calories_total");
  const currentReadiness = getLastValidMetric(filteredData, "readiness_raw") as
    | number
    | null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <KpiCard
        title="Readiness"
        value={formatNumber(currentReadiness, 2)}
        icon={<Zap className="w-4 h-4 text-yellow-500" />}
        colorClass={getReadinessColor(currentReadiness)}
      />
      <KpiCard
        title="Avg RHR"
        value={`${avgRHR} bpm`}
        icon={<Activity className="w-4 h-4 text-rose-500" />}
      />
      <KpiCard
        title="Avg Sleep"
        value={avgSleep}
        icon={<Moon className="w-4 h-4 text-indigo-400" />}
      />
      <KpiCard
        title="Avg Calories"
        value={parseInt(avgCals).toLocaleString()}
        icon={<TrendingUp className="w-4 h-4 text-orange-500" />}
      />
    </div>
  );
}

// --- Sub Component ---
function KpiCard({
  title,
  value,
  icon,
  colorClass = "text-slate-50",
}: KpiCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm transition-all hover:border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
          {title}
        </h3>
        {icon}
      </div>
      <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
    </div>
  );
}

// Helper
function getReadinessColor(val: number | null) {
  if (val === null) return "text-slate-500";
  if (val > 1) return "text-emerald-400";
  if (val < -1) return "text-rose-400";
  return "text-blue-400";
}
