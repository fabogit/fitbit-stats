import type { StartBody } from "@/features/job/startJob";
import {
  AGE_YEARS_MAX,
  AGE_YEARS_MIN,
  HEIGHT_CM_MAX,
  HEIGHT_CM_MIN,
  WEIGHT_KG_MAX,
  WEIGHT_KG_MIN,
} from "@/lib/biometrics";
import { RELATIVE_PATH_ERROR, isDesktopRelativePath } from "./usePathCheck";
import type { ProfileValues } from "./useProfileForm";

export type FieldErrors = Partial<Record<keyof ProfileValues, string>>;
export type Validation = { ok: true; body: StartBody } | { ok: false; errors: FieldErrors };

/** The text of a number field as a finite number, or null if it is empty or not a number. */
function toNumber(text: string): number | null {
  if (text.trim() === "") return null;
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}

/** At most one decimal place, with room for floating-point noise (70.1 * 10 is not exactly 701). */
const hasAtMostOneDecimal = (n: number) => Math.abs(n * 10 - Math.round(n * 10)) < 1e-9;

/**
 * The one place that decides whether the profile may be sent to the server.
 * Same limits as `lib/biometrics`: a whole number of centimetres, a weight with
 * at most one decimal, a date of birth inside `dob`.
 */
export function validateProfile(v: ProfileValues, dob: { min: string; max: string }): Validation {
  const errors: FieldErrors = {};
  const height = toNumber(v.height);
  const weight = toNumber(v.weight);
  const path = v.data_path.trim();

  if (!v.dob || v.dob < dob.min || v.dob > dob.max) {
    errors.dob = `Please enter a valid Date of Birth (age ${AGE_YEARS_MIN}-${AGE_YEARS_MAX})`;
  }
  if (v.gender !== "male" && v.gender !== "female") {
    errors.gender = "Please select a gender";
  }
  if (
    height === null ||
    !Number.isInteger(height) ||
    height < HEIGHT_CM_MIN ||
    height > HEIGHT_CM_MAX
  ) {
    errors.height = `Please enter a valid height (${HEIGHT_CM_MIN}-${HEIGHT_CM_MAX} cm, whole number)`;
  }
  if (
    weight === null ||
    !hasAtMostOneDecimal(weight) ||
    weight < WEIGHT_KG_MIN ||
    weight > WEIGHT_KG_MAX
  ) {
    errors.weight = `Please enter a valid weight (${WEIGHT_KG_MIN}-${WEIGHT_KG_MAX} kg, at most one decimal)`;
  }
  if (!path) errors.data_path = "Datastore path is required";
  else if (isDesktopRelativePath(path)) errors.data_path = RELATIVE_PATH_ERROR;

  if (Object.keys(errors).length > 0 || height === null || weight === null) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    body: { dob: v.dob, gender: v.gender, height, weight, data_path: path },
  };
}
