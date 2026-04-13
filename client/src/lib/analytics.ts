import type { HealthRecord } from "@/types/health";

export const formatNumber = (
  num: number | null | undefined,
  decimals = 1
): string => {
  if (num === null || num === undefined) return "--";
  return num.toFixed(decimals);
};

/**
 * Common stats calculation for any numeric array
 */
export const calculateStats = (series: number[], decimals = 1) => {
  if (series.length === 0) return { avg: "--", min: "--", max: "--" };
  const sum = series.reduce((a, b) => a + b, 0);
  return {
    avg: (sum / series.length).toFixed(decimals),
    min: Math.min(...series).toFixed(decimals),
    max: Math.max(...series).toFixed(decimals),
  };
};

/**
 * Filters and returns a valid series of numbers for a specific metric.
 */
export const getValidSeries = (
  data: HealthRecord[],
  key: keyof HealthRecord
): number[] => {
  const rawValues = data
    .map((d) => d[key])
    .filter((v): v is number => v !== null && v !== undefined);

  switch (key) {
    case "resting_bpm":
    case "rmssd":
    case "overall_score":
    case "stress_score":
      return rawValues.filter((v) => v > 0);
    case "calories_total":
      return rawValues.filter((v) => v > 500);
    case "spo2_avg":
      return rawValues.filter((v) => v > 80);
    default:
      return rawValues;
  }
};

export const calculateAverage = (data: HealthRecord[], key: keyof HealthRecord): string => 
  calculateStats(getValidSeries(data, key)).avg;

export const calculateMin = (data: HealthRecord[], key: keyof HealthRecord): string => 
  calculateStats(getValidSeries(data, key)).min;

export const calculateMax = (data: HealthRecord[], key: keyof HealthRecord): string => 
  calculateStats(getValidSeries(data, key)).max;

/**
 * Synthetic Series: Recovery Score (calculated daily)
 */
export const getRecoveryScoreSeries = (data: HealthRecord[]): number[] => {
  return data.map(record => {
    const hrv = record.rmssd;
    const rhr = record.resting_bpm;
    const sleep = record.overall_score;

    if (!hrv || !rhr || !sleep || hrv <= 0 || rhr <= 0 || sleep <= 0) return null;

    const hrvScore = Math.min(100, (hrv / 70) * 100);
    const rhrScore = Math.max(0, Math.min(100, ((85 - rhr) / (85 - 45)) * 100));
    const sleepScore = sleep;

    return Math.round(hrvScore * 0.4 + rhrScore * 0.3 + sleepScore * 0.3);
  }).filter((v): v is number => v !== null);
};

/**
 * Synthetic Series: Restorative Sleep % (calculated daily)
 */
export const getRestorativeSleepSeries = (data: HealthRecord[]): number[] => {
  return data.map(record => {
    const total = record.sleep_deep + record.sleep_light + record.sleep_rem + record.sleep_awake;
    const restorative = record.sleep_deep + record.sleep_rem;
    if (total <= 0) return null;
    return (restorative / total) * 100;
  }).filter((v): v is number => v !== null);
};

/**
 * Synthetic Series: Readiness (Z-Score raw)
 */
export const getReadinessSeries = (data: HealthRecord[]): number[] => {
  return data
    .map(record => record.readiness_raw)
    .filter((v): v is number => v !== null);
};

export const getLastValidMetric = (data: HealthRecord[], key: keyof HealthRecord) => {
  for (let i = data.length - 1; i >= 0; i--) {
    const val = data[i][key];
    if (val !== null && val !== undefined) {
      const seriesCheck = getValidSeries([data[i]], key);
      if (seriesCheck.length > 0) return val;
    }
  }
  return null;
};

export const calculateRecoveryScore = (data: HealthRecord[]): number | null => {
  const series = getRecoveryScoreSeries(data);
  return series.length > 0 ? series[series.length - 1] : null;
};
