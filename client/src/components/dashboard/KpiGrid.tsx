import { type ReactNode, useMemo, memo } from "react";
import { useAppSelector } from "@/store/store";
import {
  calculateStats,
  getValidSeries,
  getRecoveryScoreSeries,
  getRestorativeSleepSeries,
  getReadinessSeries,
  formatNumber,
} from "@/lib/analytics";
import {
  TrendingUp,
  Activity,
  Moon,
  Zap,
  HeartPulse,
  Droplet,
  BrainCircuit,
  ArrowDown,
  ArrowUp,
} from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { selectFilteredData } from "@/features/dashboard/dashboardSlice";

// --- Type Definitions ---
interface KpiCardProps {
  title: string;
  value: string | number;
  min?: string | number;
  max?: string | number;
  icon: ReactNode;
  colorClass?: string;
  tooltipContent?: ReactNode;
  unit?: string;
}

// --- Main Component ---
export const KpiGrid = memo(function KpiGrid() {
  const filteredData = useAppSelector(selectFilteredData);

  const metrics = useMemo(() => {
    if (filteredData.length === 0) return null;

    const rhrStats = calculateStats(getValidSeries(filteredData, "resting_bpm"));
    const sleepStats = calculateStats(getValidSeries(filteredData, "overall_score"));
    const calsStats = calculateStats(getValidSeries(filteredData, "calories_total"), 0);
    const hrvStats = calculateStats(getValidSeries(filteredData, "rmssd"));
    const spo2Stats = calculateStats(getValidSeries(filteredData, "spo2_avg"));
    const stressStats = calculateStats(getValidSeries(filteredData, "stress_score"));
    
    // Synthetic Series
    const recoverySeries = getRecoveryScoreSeries(filteredData);
    const recoveryStats = calculateStats(recoverySeries, 0);
    
    const readinessSeries = getReadinessSeries(filteredData);
    const readinessStats = calculateStats(readinessSeries, 2);
    
    const restorativeSeries = getRestorativeSleepSeries(filteredData);
    const restorativeStats = calculateStats(restorativeSeries, 1);

    return {
      rhr: rhrStats,
      sleep: sleepStats,
      cals: calsStats,
      hrv: hrvStats,
      spo2: spo2Stats,
      stress: stressStats,
      recovery: recoveryStats,
      readiness: readinessStats,
      restorative: restorativeStats,
      lastRecovery: recoverySeries.length > 0 ? recoverySeries[recoverySeries.length - 1] : null,
      lastReadiness: readinessSeries.length > 0 ? readinessSeries[readinessSeries.length - 1] : null,
    };
  }, [filteredData]);

  if (!metrics) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 md:px-0">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
        <KpiCard
          title="Recovery Score"
          value={metrics.lastRecovery ?? "--"}
          min={metrics.recovery.min}
          max={metrics.recovery.max}
          icon={<Zap className="w-5 h-5 text-indigo-500" />}
          colorClass={getRecoveryColor(metrics.lastRecovery)}
          tooltipContent={
            <span>
              Daily recovery status based on HRV, RHR, and Sleep.<br /><br />
              <strong className="text-indigo-400">80-100:</strong> Optimal recovery, test your limits.<br />
              <strong className="text-rose-400">&lt;60:</strong> High strain, consider active recovery or rest.
            </span>
          }
        />
        <KpiCard
          title="Readiness"
          value={formatNumber(metrics.lastReadiness, 2)}
          min={metrics.readiness.min}
          max={metrics.readiness.max}
          icon={<Zap className="w-5 h-5 text-yellow-500" />}
          colorClass={getReadinessColor(metrics.lastReadiness)}
          tooltipContent={
            <span>
              Current "form" expressed as Z-Score.<br /><br />
              Indicates performance readiness relative to your personal historical standard.
            </span>
          }
        />
        <KpiCard
          title="HRV (rMSSD)"
          value={metrics.hrv.avg}
          min={metrics.hrv.min}
          max={metrics.hrv.max}
          unit="ms"
          icon={<HeartPulse className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />}
          tooltipContent={
            <span>
              <strong>Heart Rate Variability:</strong> Time variation between heartbeats.<br /><br />
              Higher values indicate a balanced autonomic nervous system ready for stress.
            </span>
          }
        />
        <KpiCard
          title="Stress Score"
          value={metrics.stress.avg}
          min={metrics.stress.min}
          max={metrics.stress.max}
          icon={<BrainCircuit className="w-5 h-5 text-purple-500 dark:text-purple-400" />}
          tooltipContent={
            <span>
              Stress Management Score (0-100).<br /><br />
              Higher values suggest your body is handling physical and mental stress effectively.
            </span>
          }
        />
        <KpiCard
          title="Resting HR"
          value={metrics.rhr.avg}
          min={metrics.rhr.min}
          max={metrics.rhr.max}
          unit="bpm"
          icon={<Activity className="w-5 h-5 text-rose-500" />}
          tooltipContent={
            <span>
              Resting Heart Rate.<br /><br />
              An upward trend might indicate fatigue, overtraining, or early signs of illness.
            </span>
          }
        />
        <KpiCard
          title="Restorative Sleep"
          value={metrics.restorative.avg !== "--" ? `${metrics.restorative.avg}%` : "--"}
          min={metrics.restorative.min !== "--" ? `${metrics.restorative.min}%` : "--"}
          max={metrics.restorative.max !== "--" ? `${metrics.restorative.max}%` : "--"}
          icon={<Moon className="w-5 h-5 text-indigo-500 dark:text-indigo-400" />}
          tooltipContent={
            <span>
              Percentage of sleep spent in "Restorative" stages (Deep + REM).<br /><br />
              Targets: 40-50% for optimal physical and cognitive recovery.
            </span>
          }
        />
        <KpiCard
          title="Sleep Score"
          value={metrics.sleep.avg}
          min={metrics.sleep.min}
          max={metrics.sleep.max}
          icon={<Moon className="w-5 h-5 text-slate-400" />}
          tooltipContent={
            <span>Fitbit's overall sleep quality index (0-100) based on duration and stages.</span>
          }
        />
        <KpiCard
          title="SpO2"
          value={metrics.spo2.avg}
          min={metrics.spo2.min}
          max={metrics.spo2.max}
          unit="%"
          icon={<Droplet className="w-5 h-5 text-sky-500 dark:text-sky-400" />}
          tooltipContent={
            <span>Average blood oxygen saturation during sleep.<br /><br />Normal range: 95-100%.</span>
          }
        />
        <KpiCard
          title="Daily Calories"
          value={parseInt(metrics.cals.avg.replace("--", "0")).toLocaleString()}
          min={parseInt(metrics.cals.min.replace("--", "0")).toLocaleString()}
          max={parseInt(metrics.cals.max.replace("--", "0")).toLocaleString()}
          icon={<TrendingUp className="w-5 h-5 text-orange-500" />}
          tooltipContent={
            <span>Total daily energy expenditure (BMR + Physical Activity).</span>
          }
        />
      </div>
    </div>
  );
});

function KpiCard({ title, value, min, max, icon, colorClass = "text-card-foreground", tooltipContent, unit = "" }: KpiCardProps) {
  const hasRange = min !== undefined && max !== undefined && min !== "--";

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm transition-all hover:border-primary/50 hover:shadow-md flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          {tooltipContent && (
            <div className="mr-2 -ml-1">
              <InfoTooltip content={tooltipContent} />
            </div>
          )}
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</h3>
        </div>
        {icon}
      </div>

      <div className="flex flex-col items-center">
        <div className={`text-4xl font-bold ${colorClass} tracking-tight mb-1`}>
          {value}
          {unit && <span className="text-lg font-medium ml-1 opacity-70">{unit}</span>}
        </div>
        
        {hasRange && (
          <div className="flex items-center gap-4 mt-2 py-1 px-3 bg-muted/30 rounded-full text-[10px] font-medium text-muted-foreground">
            <div className="flex items-center gap-1">
              <ArrowDown className="w-3 h-3 text-rose-500" />
              <span>Min: {min}</span>
            </div>
            <div className="w-1 h-1 rounded-full bg-border" />
            <div className="flex items-center gap-1">
              <ArrowUp className="w-3 h-3 text-emerald-500" />
              <span>Max: {max}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function getRecoveryColor(val: number | null) {
  if (val === null) return "text-muted-foreground";
  if (val >= 80) return "text-indigo-600 dark:text-indigo-400 font-extrabold";
  if (val >= 70) return "text-emerald-600 dark:text-emerald-400";
  if (val < 60) return "text-rose-600 dark:text-rose-400";
  return "text-blue-600 dark:text-blue-400";
}

function getReadinessColor(val: number | null) {
  if (val === null) return "text-muted-foreground";
  if (val > 1) return "text-emerald-600 dark:text-emerald-400";
  if (val < -1) return "text-rose-600 dark:text-rose-400";
  return "text-blue-600 dark:text-blue-400";
}
