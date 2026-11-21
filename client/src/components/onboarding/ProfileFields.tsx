import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { HEIGHT_CM_MIN, HEIGHT_CM_MAX, WEIGHT_KG_MIN, WEIGHT_KG_MAX } from "@/lib/biometrics";
import type { FieldErrors } from "./validation";
import type { Gender, ProfileValues } from "./useProfileForm";

interface ProfileFieldsProps {
  values: Pick<ProfileValues, "dob" | "gender" | "height" | "weight">;
  errors: FieldErrors;
  dobBounds: { min: string; max: string };
  onChange(patch: Partial<ProfileValues>): void;
  disabled?: boolean;
}

/** The message under a field; `id` is what the field's `aria-describedby` points to. */
export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="text-xs text-red-500 animate-in fade-in slide-in-from-top-1">
      {message}
    </p>
  );
}

const inputClass = (value: string, error?: string) =>
  `h-12 text-lg transition-all duration-300 ${!value ? "text-muted-foreground/40" : ""} ${
    error ? "border-red-500/50 bg-red-500/5" : ""
  }`;

/** What a field needs to be linked to its error message. */
const a11y = (id: string, error?: string) => ({
  "aria-invalid": error ? true : undefined,
  "aria-describedby": error ? `${id}-error` : undefined,
});

/** Date of birth, height, weight and gender, each with its error underneath. */
export function ProfileFields({
  values,
  errors,
  dobBounds,
  onChange,
  disabled,
}: ProfileFieldsProps) {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2 text-left">
          <Label htmlFor="dob">Date of Birth</Label>
          <Input
            id="dob"
            type="date"
            min={dobBounds.min}
            max={dobBounds.max}
            required
            disabled={disabled}
            value={values.dob}
            onChange={(e) => onChange({ dob: e.target.value })}
            className={inputClass(values.dob, errors.dob)}
            placeholder="YYYY-MM-DD"
            {...a11y("dob", errors.dob)}
          />
          <FieldError id="dob-error" message={errors.dob} />
        </div>
        <div className="space-y-2 text-left">
          <Label htmlFor="height">Height (cm)</Label>
          <Input
            id="height"
            type="number"
            min={HEIGHT_CM_MIN}
            max={HEIGHT_CM_MAX}
            step="1"
            required
            disabled={disabled}
            placeholder="e.g. 175 cm"
            value={values.height}
            onFocus={(e) => e.target.select()}
            onChange={(e) => onChange({ height: e.target.value })}
            className={inputClass(values.height, errors.height)}
            {...a11y("height", errors.height)}
          />
          <FieldError id="height-error" message={errors.height} />
        </div>
        <div className="space-y-2 text-left">
          <Label htmlFor="weight">Weight (kg)</Label>
          <Input
            id="weight"
            type="number"
            min={WEIGHT_KG_MIN}
            max={WEIGHT_KG_MAX}
            step="0.1"
            required
            disabled={disabled}
            placeholder="e.g. 70.0 kg"
            value={values.weight}
            onFocus={(e) => e.target.select()}
            onChange={(e) => onChange({ weight: e.target.value })}
            className={inputClass(values.weight, errors.weight)}
            {...a11y("weight", errors.weight)}
          />
          <FieldError id="weight-error" message={errors.weight} />
        </div>
      </div>

      <div className="space-y-2 text-left">
        <Label htmlFor="gender">Gender</Label>
        <Select
          value={values.gender}
          required
          disabled={disabled}
          onValueChange={(value) => onChange({ gender: value as Gender })}
        >
          <SelectTrigger
            id="gender"
            className={errors.gender ? "border-red-500/50 bg-red-500/5" : undefined}
            {...a11y("gender", errors.gender)}
          >
            <SelectValue placeholder="Select gender" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="male">Male</SelectItem>
            <SelectItem value="female">Female</SelectItem>
          </SelectContent>
        </Select>
        <FieldError id="gender-error" message={errors.gender} />
      </div>
    </>
  );
}
