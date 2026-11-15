// Biometric limits. Keep identical to server/api.py (all bounds inclusive).
export const HEIGHT_CM_MIN = 50;
export const HEIGHT_CM_MAX = 250;
export const WEIGHT_KG_MIN = 20;
export const WEIGHT_KG_MAX = 300;
export const AGE_YEARS_MIN = 5;
export const AGE_YEARS_MAX = 120;

const pad = (n: number) => String(n).padStart(2, "0");

export function toDateInputValue(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// Same month/day `years` ago; 29 February falls back to 28 February.
function yearsAgo(today: Date, years: number): Date {
  const day = today.getMonth() === 1 && today.getDate() === 29 ? 28 : today.getDate();
  return new Date(today.getFullYear() - years, today.getMonth(), day);
}

// Allowed range for the date-of-birth input, computed from today:
// age between AGE_YEARS_MIN and AGE_YEARS_MAX completed years.
export function dobBounds(today: Date = new Date()): { min: string; max: string } {
  const earliest = yearsAgo(today, AGE_YEARS_MAX + 1);
  earliest.setDate(earliest.getDate() + 1);
  return {
    min: toDateInputValue(earliest),
    max: toDateInputValue(yearsAgo(today, AGE_YEARS_MIN)),
  };
}
