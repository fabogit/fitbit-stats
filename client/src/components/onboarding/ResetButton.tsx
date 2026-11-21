import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Notice } from "@/components/ui/notice";
import { apiFetch } from "@/lib/api";
import { useAppDispatch } from "../../store/store";
import { fetchHealthData } from "../../features/dashboard/dashboardSlice";

interface ResetButtonProps {
  disabled: boolean;
  /** The data was deleted: the form empties. */
  onCleared(): void;
  /** What happened, for the form to show next to the buttons. */
  onOutcome(notice: Notice): void;
}

const BUSY_TEXT = "A calculation is running. Wait for it to finish before deleting data.";

/** Factory reset: deletes the saved profile and the calculated data. */
export function ResetButton({ disabled, onCleared, onOutcome }: ResetButtonProps) {
  const dispatch = useAppDispatch();
  const [pending, setPending] = useState(false);

  const handleClearData = async () => {
    const isConfirmed = window.confirm(
      "Are you sure you want to delete all configuration and health data? This cannot be undone.",
    );
    if (!isConfirmed) return;

    setPending(true);
    try {
      const resp = await apiFetch("/api/clear", { method: "DELETE" });
      if (resp.status === 409) {
        const body = (await resp.json().catch(() => null)) as { detail?: unknown } | null;
        const detail = typeof body?.detail === "string" ? body.detail : BUSY_TEXT;
        onOutcome({ kind: "error", text: detail });
        return;
      }
      if (!resp.ok) {
        onOutcome({ kind: "error", text: `Could not delete the data (HTTP ${resp.status}).` });
        return;
      }
      onCleared();
      // The empty data makes the dashboard show its "no data" state.
      dispatch(fetchHealthData());
      onOutcome({ kind: "success", text: "All data deleted." });
    } catch (e) {
      console.error("Error clearing data:", e);
      onOutcome({ kind: "error", text: "Could not reach the local server." });
    } finally {
      setPending(false);
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      className="h-12 w-12 p-0 flex-shrink-0 text-red-500 hover:text-red-600 hover:bg-red-500/10 border-red-500/20"
      onClick={handleClearData}
      disabled={disabled || pending}
      title="Factory Reset: Clear all data"
    >
      <Trash2 className="w-5 h-5" />
    </Button>
  );
}
