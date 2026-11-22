import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface StartupScreenProps {
  /**
   * "starting": waiting for the local server. "unreachable": it did not answer in time.
   * "failed" (desktop): the shell could not start it, with the reason in `message`.
   */
  kind: "starting" | "unreachable" | "failed";
  onRetry: () => void;
  /** Failed only: the reason, and where the log file is. */
  message?: string;
  logPath?: string | null;
  /** Failed only: starts the server again. */
  onRestart?: () => void;
}

/** Shown instead of the dashboard (and instead of the first-run page) until the server answers. */
export function StartupScreen({ kind, onRetry, message, logPath, onRestart }: StartupScreenProps) {
  if (kind === "starting") {
    return (
      <div
        role="status"
        data-testid="startup-waiting"
        className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 text-muted-foreground"
      >
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p>Starting local server…</p>
      </div>
    );
  }

  if (kind === "failed") {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div
          role="alert"
          data-testid="startup-failed"
          className="flex flex-col items-center justify-center p-12 text-center bg-card/50 border border-destructive/40 rounded-3xl max-w-2xl"
        >
          <AlertTriangle className="w-12 h-12 text-destructive mb-4" />
          <h3 className="text-2xl font-extrabold tracking-tight mb-2">The local server could not start</h3>
          <p className="text-muted-foreground mb-2 break-words max-w-full">
            {message ?? "The server stopped."}
          </p>
          {logPath && (
            <p className="text-xs text-muted-foreground mb-6 break-all max-w-full">
              Details are in the log file: {logPath}
            </p>
          )}
          <Button onClick={onRestart} className={logPath ? "" : "mt-4"}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Restart server
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div
        role="alert"
        data-testid="startup-error"
        className="flex flex-col items-center justify-center p-12 text-center bg-card/50 border border-destructive/40 rounded-3xl max-w-2xl"
      >
        <AlertTriangle className="w-12 h-12 text-destructive mb-4" />
        <h3 className="text-2xl font-extrabold tracking-tight mb-2">Could not reach the local server</h3>
        <p className="text-muted-foreground mb-6 break-words max-w-full">
          The server did not answer. Check that it is running, then try again.
        </p>
        <Button onClick={onRetry}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    </div>
  );
}
