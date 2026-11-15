export interface DateRange {
  end: string;
  start: string;
}

export interface HealthRecord {
  date: string;
  resting_bpm: number | null;
  weight: number | null;
  bmi: number | null;
  calories_total: number;
  bmr: number;
  active_calories: number;
  intensity_index: number;
  overall_score: number | null;

  // Activity Detail
  very_active_minutes: number;
  moderately_active_minutes: number;
  lightly_active_minutes: number;
  sedentary_minutes: number;

  // Readiness
  readiness_raw: number | null;

  // Sleep Stages (null on days without a sleep record)
  sleep_deep: number | null;
  sleep_light: number | null;
  sleep_rem: number | null;
  sleep_awake: number | null;

  // Physiology
  rmssd: number | null; // HRV
  stress_score: number | null; // Stress
  spo2_avg: number | null;
}
