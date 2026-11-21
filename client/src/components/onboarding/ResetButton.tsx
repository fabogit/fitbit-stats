import { useRef, useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Notice } from "@/components/ui/notice";
import { apiFetch } from "@/lib/api";
import { useAppDispatch, useAppSelector } from "../../store/store";
import { fetchHealthData } from "../../features/dashboard/dashboardSlice";
import { selectIsRunning } from "../../features/job/jobSlice";

interface ResetButtonProps {
  /** A start request is in flight, or a calculation is running. */
  disabled: boolean;
  /** The data was deleted: the form empties. */
  onCleared(): void;
  /** What happened, for the form to show next to the buttons. */
  onOutcome(notice: Notice): void;
}

const BUSY_TEXT = "A calculation is running. Wait for it to finish before deleting data.";

/**
 * Factory reset: a trash button that asks for confirmation in a dialog, then
 * deletes the saved profile and the calculated data. The dialog closes on every
 * outcome; the form shows what happened.
 */
export function ResetButton({ disabled, onCleared, onOutcome }: ResetButtonProps) {
  const dispatch = useAppDispatch();
  const running = useAppSelector(selectIsRunning);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  const runReset = async () => {
    setPending(true);
    try {
      const resp = await apiFetch("/api/clear", { method: "DELETE" });
      if (resp.status === 409) {
        // The state may have changed since the button was enabled: the server decides.
        const body = (await resp.json().catch(() => null)) as { detail?: unknown } | null;
        const detail = typeof body?.detail === "string" ? body.detail : BUSY_TEXT;
        onOutcome({ kind: "error", text: detail });
      } else if (!resp.ok) {
        onOutcome({ kind: "error", text: `Could not delete the data (HTTP ${resp.status}).` });
      } else {
        onCleared();
        // The empty data makes the dashboard show its "no data" state.
        dispatch(fetchHealthData());
        onOutcome({ kind: "success", text: "All data deleted." });
      }
    } catch (e) {
      console.error("Error clearing data:", e);
      onOutcome({ kind: "error", text: "Could not reach the local server." });
    } finally {
      setPending(false);
      setOpen(false);
    }
  };

  return (
    <>
      <Button
        ref={triggerRef}
        type="button"
        variant="outline"
        className="h-12 w-12 p-0 flex-shrink-0 text-red-500 hover:text-red-600 hover:bg-red-500/10 border-red-500/20"
        onClick={() => setOpen(true)}
        disabled={disabled}
        title={running ? "Wait for the calculation to finish" : "Factory Reset: Clear all data"}
        aria-label="Factory reset"
      >
        <Trash2 className="w-5 h-5" />
      </Button>
      {/* Esc closes only this dialog: Radix closes the top layer of the stack. */}
      <Dialog open={open} onOpenChange={(next) => !pending && setOpen(next)}>
        <DialogContent
          role="alertdialog"
          className="sm:max-w-md"
          onOpenAutoFocus={(e) => {
            // Enter by mistake must not delete anything.
            e.preventDefault();
            cancelRef.current?.focus();
          }}
          onCloseAutoFocus={(e) => {
            // There is no Dialog.Trigger, so Radix does not know where to return.
            e.preventDefault();
            triggerRef.current?.focus();
          }}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <DialogHeader>
            <DialogTitle>Delete all data?</DialogTitle>
            <DialogDescription>
              This deletes your saved profile and the calculated health data. Your Fitbit export
              files are not touched. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              ref={cancelRef}
              type="button"
              variant="outline"
              disabled={pending}
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="button" variant="destructive" disabled={pending} onClick={runReset}>
              {pending && <Loader2 className="animate-spin" />}
              Delete all data
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
