import type { HealthRecord } from "@/types/health";

export const formatNumber = (
  num: number | null | undefined,
  decimals = 1
): string => {
  if (num === null || num === undefined) return "--";
  return num.toFixed(decimals);
};

export const calculateAverage = (
  data: HealthRecord[],
  key: keyof HealthRecord
): string => {
  const validData = data.filter((d) => d[key] !== null && d[key] !== undefined);
  if (validData.length === 0) return "--";
  const sum = validData.reduce((acc, curr) => acc + (curr[key] as number), 0);
  return (sum / validData.length).toFixed(1);
};

export const getLastValidMetric = (
  data: HealthRecord[],
  key: keyof HealthRecord
) => {
  for (let i = data.length - 1; i >= 0; i--) {
    if (data[i][key] !== null) return data[i][key];
  }
  return null;
};

/**
 * Calculates a consolidated Recovery Score (0-100)
 * based on HRV (rMSSD), Resting BPM, and Sleep Score.
 */
export const calculateRecoveryScore = (data: HealthRecord[]): number | null => {
  if (data.length === 0) return null;
  
  const lastValidHRV = getLastValidMetric(data, "rmssd") as number | null;
  const lastValidRHR = getLastValidMetric(data, "resting_bpm") as number | null;
  const lastValidSleep = getLastValidMetric(data, "overall_score") as number | null;

  if (lastValidHRV === null || lastValidRHR === null || lastValidSleep === null) {
    return null;
  }

  // Heuristic normalization:
  // HRV: Baseline ~50ms (higher better)
  const hrvScore = Math.min(100, (lastValidHRV / 70) * 100);
  
  // RHR: Baseline ~60bpm (lower better, 45=100, 85=0)
  const rhrScore = Math.max(0, Math.min(100, ((85 - lastValidRHR) / (85 - 45)) * 100));
  
  // Sleep Quality is already 0-100
  const sleepScore = lastValidSleep;

  // Composite weighted score
  return Math.round(
    hrvScore * 0.4 +   // Physiology (HRV)
    rhrScore * 0.3 +   // Cardiovascular (RHR)
    sleepScore * 0.3   // Recovery (Sleep)
  );
};
