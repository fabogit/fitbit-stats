import type { HealthRecord } from "@/types/health";

export type ColumnStats = {
  min: number;
  p33: number;
  p66: number;
  max: number;
};

export type StatsMap = Record<string, ColumnStats>;

function getPercentiles(values: number[]): ColumnStats {
  if (values.length === 0) return { min: 0, p33: 0, p66: 0, max: 0 };

  const sorted = [...values].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];

  const p33Index = Math.floor(sorted.length * 0.33);
  const p66Index = Math.floor(sorted.length * 0.66);

  return {
    min,
    p33: sorted[p33Index],
    p66: sorted[p66Index],
    max,
  };
}

export function calculateStats(data: HealthRecord[]): StatsMap {
  const numericKeys: (keyof HealthRecord)[] = [
    "resting_bpm",
    "weight",
    "calories_total",
    "active_calories",
    "intensity_index",
    "overall_score",
    "readiness_raw",
    "rmssd",
    "stress_score",
    "spo2_avg",
    "sleep_deep",
    "sleep_rem",
  ];

  const stats: StatsMap = {};

  numericKeys.forEach((key) => {
    const values = data
      .map((d) => d[key])
      .filter(
        (v): v is number => v !== null && v !== undefined && !isNaN(v as number)
      );

    stats[key] = getPercentiles(values);
  });

  return stats;
}
