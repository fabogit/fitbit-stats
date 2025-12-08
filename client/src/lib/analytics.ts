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
