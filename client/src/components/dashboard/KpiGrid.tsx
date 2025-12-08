import type { ReactNode } from "react";
import { useAppSelector } from "@/store";
import {
  calculateAverage,
  formatNumber,
  getLastValidMetric,
} from "@/lib/analytics";
import { TrendingUp, Activity, Moon, Zap } from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

// --- Type Definitions ---
interface KpiCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  colorClass?: string;
  tooltipContent?: ReactNode;
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
        tooltipContent={
          <span>
            <strong>Z-Score Metric</strong>
            <br />
            Combines Sleep quality and RHR.
            <br />• <strong className="text-emerald-400">&gt; 1.0</strong>: Peak
            Condition
            <br />• <strong>0.0</strong>: Average
            <br />• <strong className="text-rose-400">&lt; -1.0</strong>:
            Stressed
          </span>
        }
      />
      <KpiCard
        title="Avg RHR"
        value={`${avgRHR} bpm`}
        icon={<Activity className="w-4 h-4 text-rose-500" />}
        tooltipContent={
          <span>
            <strong>Resting Heart Rate</strong>
            <br />
            Lower is generally better.
            <br />
            Spikes usually indicate stress, illness, or overtraining.
          </span>
        }
      />
      <KpiCard
        title="Avg Sleep"
        value={avgSleep}
        icon={<Moon className="w-4 h-4 text-indigo-400" />}
        tooltipContent={
          <span>
            <strong>Sleep Score (0-100)</strong>
            <br />• <strong>&gt; 80</strong>: Good
            <br />• <strong>&gt; 90</strong>: Excellent
          </span>
        }
      />
      <KpiCard
        title="Avg Calories"
        value={parseInt(avgCals).toLocaleString()}
        icon={<TrendingUp className="w-4 h-4 text-orange-500" />}
        tooltipContent={
          <span>
            <strong>Total Daily Expenditure</strong>
            <br />
            Sum of BMR (Base) + Active Calories.
          </span>
        }
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
  tooltipContent,
}: KpiCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm transition-all hover:border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            {title}
          </h3>
          {tooltipContent && <InfoTooltip content={tooltipContent} />}
        </div>
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
