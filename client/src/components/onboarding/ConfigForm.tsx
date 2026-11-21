import { useState } from "react";
import { Button } from "@/components/ui/button";
import { InlineNotice, notify, type Notice } from "@/components/ui/notice";
import { dobBounds } from "@/lib/biometrics";
import { useEtlJob } from "../../features/job/useEtlJob";
import { DataPathField } from "./DataPathField";
import { ProfileFields } from "./ProfileFields";
import { ResetButton } from "./ResetButton";
import { usePathCheck } from "./usePathCheck";
import { useProfileForm, type ProfileValues } from "./useProfileForm";
import { validateProfile, type FieldErrors } from "./validation";

interface ConfigFormProps {
  onSuccess: () => void;
  submitLabel?: string;
}

/** Shown after the dialog closes, so it says what happened to the values just entered. */
const BUSY_NOTICE =
  "A calculation was already running; its progress is shown above. Your changes were not saved.";

export function ConfigForm({ onSuccess, submitLabel = "Start Calculation" }: ConfigFormProps) {
  const form = useProfileForm();
  const job = useEtlJob();
  const check = usePathCheck(form.values.data_path, form.server === "ready");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [notice, setNotice] = useState<Notice | null>(null);

  // Editing a field clears its error: it is about the value that was just replaced.
  const change = (patch: Partial<ProfileValues>) => {
    form.set(patch);
    setErrors((prev) => {
      const next = { ...prev };
      for (const key of Object.keys(patch)) delete next[key as keyof ProfileValues];
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotice(null);
    const validation = validateProfile(form.values, dobBounds());
    setErrors(validation.ok ? {} : validation.errors);
    if (!validation.ok) return;

    const outcome = await job.start(validation.body);
    if (outcome.kind === "failed") {
      setNotice({ kind: "error", text: outcome.message });
      return;
    }
    // The dialog closes either way; the progress is the job status in the store.
    // Another run in progress means the values just entered were not used.
    if (outcome.kind === "busy") notify({ kind: "info", text: BUSY_NOTICE });
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4 text-left">
      <ProfileFields
        values={form.values}
        errors={errors}
        dobBounds={dobBounds()}
        onChange={change}
        disabled={job.starting}
      />
      <DataPathField
        value={form.values.data_path}
        onChange={(data_path) => change({ data_path })}
        check={check}
        server={form.server}
        onRetryServer={form.retryServer}
        error={errors.data_path}
        disabled={job.starting}
      />
      <InlineNotice notice={notice} onDismiss={() => setNotice(null)} />
      <div className="pt-6 flex gap-3">
        <ResetButton
          disabled={job.starting || job.running}
          onCleared={() => {
            form.clear();
            setErrors({});
          }}
          onOutcome={setNotice}
        />
        <Button
          type="button"
          variant="outline"
          className="flex-1 h-12"
          onClick={onSuccess}
          disabled={job.starting}
        >
          Skip / Close
        </Button>
        <Button
          type="submit"
          className="flex-[2] text-lg h-12 transition-all duration-300 transform active:scale-95"
          disabled={job.starting}
        >
          {job.starting ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-primary-foreground"></div>
              <span>Processing...</span>
            </div>
          ) : (
            submitLabel
          )}
        </Button>
      </div>
    </form>
  );
}
