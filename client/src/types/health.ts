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

  // Sleep Stages
  sleep_deep: number;
  sleep_light: number;
  sleep_rem: number;
  sleep_awake: number;

  // Physiology
  rmssd: number | null; // HRV
  stress_score: number | null; // Stress
  spo2_avg: number | null;
}
