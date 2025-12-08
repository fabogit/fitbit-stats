export interface DateRange {
  end: string;
  start: string;
}

export interface HealthRecord {
  active_calories: number;
  bmi: number | null;
  bmr: number;
  calories_total: number;
  date: string;
  intensity_index: number;
  lightly_active_minutes: number;
  moderately_active_minutes: number;
  overall_score: number | null;
  readiness_raw: number | null;
  resting_bpm: number | null;
  sedentary_minutes: number;
  weight: number | null;
  very_active_minutes: number;
}
