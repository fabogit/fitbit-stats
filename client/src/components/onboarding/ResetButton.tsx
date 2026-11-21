import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { useAppDispatch } from "../../store/store";
import { fetchHealthData } from "../../features/dashboard/dashboardSlice";

interface ResetButtonProps {
  disabled: boolean;
  /** The data was deleted: the form empties. */
  onCleared(): void;
}

/** Factory reset: deletes the saved profile and the calculated data. */
export function ResetButton({ disabled, onCleared }: ResetButtonProps) {
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
        alert("A calculation is running. Wait for it to finish before deleting data.");
        return;
      }
      if (!resp.ok) throw new Error(`Clear request failed (HTTP ${resp.status})`);

      onCleared();
      // Calling fetchHealthData will reload empty state causing NoDataState to re-render in Dashboard
      dispatch(fetchHealthData());
      alert("All application data has been successfully deleted.");
    } catch (e) {
      console.error("Error clearing data:", e);
      alert("Failed to clear data.");
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
