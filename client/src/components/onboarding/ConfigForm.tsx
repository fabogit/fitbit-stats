import { useState } from "react";
import { Button } from "@/components/ui/button";
import { dobBounds } from "@/lib/biometrics";
import { useAppDispatch } from "../../store/store";
import { BUSY_MESSAGE, startJob } from "../../features/job/startJob";
import { DataPathField } from "./DataPathField";
import { ProfileFields } from "./ProfileFields";
import { ResetButton } from "./ResetButton";
import { usePathCheck } from "./usePathCheck";
import { useProfileForm } from "./useProfileForm";
import { validateProfile } from "./validation";

interface ConfigFormProps {
  onSuccess: () => void;
  submitLabel?: string;
}

export function ConfigForm({ onSuccess, submitLabel = "Start Calculation" }: ConfigFormProps) {
  const dispatch = useAppDispatch();
  const form = useProfileForm();
  const check = usePathCheck(form.values.data_path, form.server === "ready");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validation = validateProfile(form.values, dobBounds());
    if (!validation.ok) {
      // A path the desktop cannot resolve is shown under the field by the path check.
      const [first, message] = Object.entries(validation.errors)[0];
      if (first !== "data_path" || message === "Datastore path is required") alert(message);
      return;
    }

    setLoading(true);
    try {
      const result = await startJob(dispatch, validation.body);
      if (result.kind === "failed") {
        alert("Error starting calculation on the server.");
        setLoading(false);
        return;
      }
      // Another run is in progress: its progress is now shown, and the values
      // just entered were not saved or used.
      if (result.kind === "busy") alert(BUSY_MESSAGE);
      // Close the form; the job status in the store shows the progress.
      setLoading(false);
      onSuccess();
    } catch (err) {
      console.error(err);
      setLoading(false);
      alert("Failed to connect to the local server.");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-left">
      <ProfileFields
        values={form.values}
        dobBounds={dobBounds()}
        onChange={form.set}
        disabled={loading}
      />
      <DataPathField
        value={form.values.data_path}
        onChange={(data_path) => form.set({ data_path })}
        check={check}
        server={form.server}
        onRetryServer={form.retryServer}
        disabled={loading}
      />
      <div className="pt-6 flex gap-3">
        <ResetButton disabled={loading} onCleared={form.clear} />
        <Button
          type="button"
          variant="outline"
          className="flex-1 h-12"
          onClick={onSuccess}
          disabled={loading}
        >
          Skip / Close
        </Button>
        <Button
          type="submit"
          className="flex-[2] text-lg h-12 transition-all duration-300 transform active:scale-95"
          disabled={loading}
        >
          {loading ? (
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
