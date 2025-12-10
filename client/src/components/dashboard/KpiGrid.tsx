import type { ReactNode } from "react";
import { useAppSelector } from "@/store";
import {
  calculateAverage,
  formatNumber,
  getLastValidMetric,
} from "@/lib/analytics";
import {
  TrendingUp,
  Activity,
  Moon,
  Zap,
  HeartPulse,
  Droplet,
  BrainCircuit,
} from "lucide-react";
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
  const avgHRV = calculateAverage(filteredData, "rmssd");
  const avgSpO2 = calculateAverage(filteredData, "spo2_avg");
  const avgStress = calculateAverage(filteredData, "stress_score");

  const currentReadiness = getLastValidMetric(filteredData, "readiness_raw") as
    | number
    | null;

  const sleepDays = filteredData.filter(
    (d) => d.sleep_deep + d.sleep_light + d.sleep_rem + d.sleep_awake > 0
  );
  let qualityPct = "--";
  if (sleepDays.length > 0) {
    const totalMins = sleepDays.reduce(
      (acc, curr) =>
        acc +
        (curr.sleep_deep +
          curr.sleep_light +
          curr.sleep_rem +
          curr.sleep_awake),
      0
    );
    const restorativeMins = sleepDays.reduce(
      (acc, curr) => acc + (curr.sleep_deep + curr.sleep_rem),
      0
    );
    if (totalMins > 0)
      qualityPct = ((restorativeMins / totalMins) * 100).toFixed(1);
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {/* 1. Readiness */}
      <KpiCard
        title="Readiness"
        value={formatNumber(currentReadiness, 2)}
        icon={<Zap className="w-5 h-5 text-yellow-500" />} // Icona w-5 h-5
        colorClass={getReadinessColor(currentReadiness)}
        tooltipContent={
          <span>
            Current Form (Z-Score).
            <br />
            &gt;1 Peak, &lt;-1 Tired.
          </span>
        }
      />

      {/* 2. HRV */}
      <KpiCard
        title="Avg HRV"
        value={avgHRV !== "--" ? `${avgHRV} ms` : "--"}
        icon={<HeartPulse className="w-5 h-5 text-emerald-400" />} // Icona w-5 h-5
        tooltipContent={
          <span>
            Heart Rate Variability (rMSSD).
            <br />
            Higher is better.
          </span>
        }
      />

      {/* 3. Stress Score */}
      <KpiCard
        title="Avg Stress Score"
        value={avgStress !== "--" ? avgStress : "--"}
        icon={<BrainCircuit className="w-5 h-5 text-purple-400" />} // Icona w-5 h-5
        tooltipContent={
          <span>
            Stress Management Score (0-100).
            <br />
            Higher = Better handling.
          </span>
        }
      />

      {/* 4. RHR */}
      <KpiCard
        title="Avg RHR"
        value={`${avgRHR} bpm`}
        icon={<Activity className="w-5 h-5 text-rose-500" />} // Icona w-5 h-5
        tooltipContent={
          <span>
            Resting Heart Rate.
            <br />
            Lower is better.
          </span>
        }
      />

      {/* 5. Restorative Sleep */}
      <KpiCard
        title="Restorative Sleep"
        value={qualityPct !== "--" ? `${qualityPct}%` : "--"}
        icon={<Moon className="w-5 h-5 text-indigo-400" />} // Icona w-5 h-5
        tooltipContent={
          <span>
            % of Deep + REM sleep.
            <br />
            Target &gt; 40%
          </span>
        }
      />

      {/* 6. Sleep Score */}
      <KpiCard
        title="Avg Sleep Score"
        value={avgSleep}
        icon={<Moon className="w-5 h-5 text-slate-400" />} // Icona w-5 h-5
        tooltipContent={<span>Overall sleep quality (0-100).</span>}
      />

      {/* 7. SpO2 */}
      <KpiCard
        title="Avg SpO2"
        value={avgSpO2 !== "--" ? `${avgSpO2}%` : "--"}
        icon={<Droplet className="w-5 h-5 text-sky-400" />} // Icona w-5 h-5
        tooltipContent={
          <span>
            Blood Oxygen.
            <br />
            Healthy: 95-100%
          </span>
        }
      />

      {/* 8. Calories */}
      <KpiCard
        title="Avg Calories"
        value={parseInt(avgCals.replace("--", "0")).toLocaleString()}
        icon={<TrendingUp className="w-5 h-5 text-orange-500" />} // Icona w-5 h-5
        tooltipContent={<span>Total Daily Burn (BMR + Active).</span>}
      />
    </div>
  );
}
// --- KpiCard Component ---
// --- Sub Component Aggiornato ---
function KpiCard({
  title,
  value,
  icon,
  colorClass = "text-slate-50",
  tooltipContent,
}: KpiCardProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm transition-all hover:border-slate-700 hover:shadow-md hover:shadow-indigo-500/10">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          {tooltipContent && (
            <div className="mr-2 -ml-1">
              <InfoTooltip content={tooltipContent} />
            </div>
          )}
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
            {title}
          </h3>
        </div>
        {icon}
      </div>

      <div
        className={`text-3xl font-bold ${colorClass} tracking-tight text-center`}
      >
        {value}
      </div>
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
