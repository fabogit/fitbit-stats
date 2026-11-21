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
import type { Gender, ProfileValues } from "./useProfileForm";

interface ProfileFieldsProps {
  values: Pick<ProfileValues, "dob" | "gender" | "height" | "weight">;
  dobBounds: { min: string; max: string };
  onChange(patch: Partial<ProfileValues>): void;
  disabled?: boolean;
}

const inputClass = (value: string) =>
  `h-12 text-lg transition-all duration-300 ${!value ? "text-muted-foreground/40" : ""}`;

/** Date of birth, height, weight and gender. */
export function ProfileFields({ values, dobBounds, onChange, disabled }: ProfileFieldsProps) {
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
            className={inputClass(values.dob)}
            placeholder="YYYY-MM-DD"
          />
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
            className={inputClass(values.height)}
          />
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
            className={inputClass(values.weight)}
          />
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
          <SelectTrigger id="gender">
            <SelectValue placeholder="Select gender" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="male">Male</SelectItem>
            <SelectItem value="female">Female</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
