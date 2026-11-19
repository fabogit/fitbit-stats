import { useState } from "react";
import { AlertTriangle, XCircle, X } from "lucide-react";
import { useAppSelector } from "../../store/store";
import { selectFailureMessage, selectWarnings } from "@/features/job/jobSlice";

/**
 * Says what the last calculation left behind: why it failed, and the files it
 * had to skip, so a failure or partial data is never silent. Both come from
 * the job status, so every client shows them and they survive a restart.
 */
export function EtlWarningsBanner() {
  const warnings = useAppSelector(selectWarnings);
  const failure = useAppSelector(selectFailureMessage);
  // Dismissal applies to this exact set of warnings; a new run shows them again.
  const signature = JSON.stringify(warnings);
  const [dismissed, setDismissed] = useState<string | null>(null);

  const showWarnings = warnings.length > 0 && dismissed !== signature;
  if (failure === null && !showWarnings) return null;

  return (
    <>
      {failure !== null && (
        // Stays until the next calculation starts: nothing to dismiss.
        <div
          role="alert"
          data-testid="etl-error-banner"
          className="border-b border-red-500/40 bg-red-500/10 px-4 md:px-8 py-3"
        >
          <div className="flex items-start gap-3">
            <XCircle className="w-4 h-4 mt-0.5 text-red-500 shrink-0" />
            <p className="flex-1 min-w-0 text-sm font-semibold break-words">
              Last calculation failed: {failure}
            </p>
          </div>
        </div>
      )}
      {showWarnings && (
        <div
          role="status"
          data-testid="etl-warnings-banner"
          className="border-b border-amber-500/40 bg-amber-500/10 px-4 md:px-8 py-3"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-500 shrink-0" />
            <div className="flex-1 min-w-0 text-sm">
              <p className="font-semibold">
                {warnings.length} file{warnings.length === 1 ? "" : "s"} could not be read and{" "}
                {warnings.length === 1 ? "was" : "were"} skipped. Some data may be missing.
              </p>
              <ul className="mt-1 text-muted-foreground space-y-0.5 max-h-24 overflow-y-auto">
                {warnings.map((w, i) => (
                  <li key={`${w.file}-${i}`} className="truncate" title={w.reason}>
                    <span className="font-medium text-foreground">{w.file}</span>: {w.reason}
                  </li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              aria-label="Dismiss warning"
              onClick={() => setDismissed(signature)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
