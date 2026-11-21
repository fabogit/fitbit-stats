import { useRef } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { CheckCircle2, AlertCircle, Search, Loader2 } from "lucide-react";
import type { PathCheck } from "./usePathCheck";
import type { ServerState } from "./useProfileForm";

interface DataPathFieldProps {
  value: string;
  onChange(path: string): void;
  check: PathCheck;
  server: ServerState;
  onRetryServer(): void;
  disabled?: boolean;
}

/** The export folder: path input, Browse (folder dialog), server check and help. */
export function DataPathField({
  value,
  onChange,
  check,
  server,
  onRetryServer,
  disabled,
}: DataPathFieldProps) {
  const selectOnClick = useRef(false);

  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const relativePath = (files[0] as unknown as { webkitRelativePath: string })
        .webkitRelativePath;
      if (relativePath) onChange(`./${relativePath.split("/")[0]}`);
    }
  };

  const handleBrowse = async () => {
    // Check if running inside Tauri
    if (isTauri()) {
      try {
        const selectedPath = await open({
          directory: true,
          multiple: false,
          title: "Select Fitbit Export Folder",
        });
        if (selectedPath && typeof selectedPath === "string") onChange(selectedPath);
      } catch (err) {
        console.error("Failed to open Tauri dialog:", err);
      }
    } else {
      // Fallback for web mode
      document.getElementById("folder-picker")?.click();
    }
  };

  return (
    <div className="space-y-2 pt-2 text-left">
      <div className="flex items-center justify-between">
        <Label htmlFor="data_path" className="text-muted-foreground">
          Datastore Path (Folder)
        </Label>
        <div className="flex items-center gap-2">
          <input
            type="file"
            id="folder-picker"
            className="hidden"
            {...({
              webkitdirectory: "",
              directory: "",
            } as unknown as React.InputHTMLAttributes<HTMLInputElement>)}
            onChange={handleFolderSelect}
          />
          <Button
            type="button"
            variant="link"
            size="sm"
            className="h-auto p-0 text-xs text-primary/70 hover:text-primary transition-colors"
            onClick={handleBrowse}
            disabled={disabled}
          >
            <Search className="w-3 h-3 mr-1" />
            Browse...
          </Button>
        </div>
      </div>
      <div className="relative group">
        <Input
          id="data_path"
          type="text"
          placeholder={isTauri() ? "Click Browse to choose the folder" : "./data"}
          value={value}
          disabled={disabled}
          onFocus={(e) => e.target.select()}
          // The desktop WebView clears the selection on the click that gave
          // the field focus, so select again on click (first click only).
          onMouseDown={(e) => {
            selectOnClick.current = document.activeElement !== e.currentTarget;
          }}
          onClick={(e) => {
            const input = e.currentTarget;
            if (selectOnClick.current) setTimeout(() => input.select(), 0);
            selectOnClick.current = false;
          }}
          onChange={(e) => onChange(e.target.value)}
          className={`h-12 pr-24 transition-colors ${
            check.status === "valid"
              ? "border-green-500/50 bg-green-500/5"
              : check.status === "invalid"
                ? "border-red-500/50 bg-red-500/5"
                : ""
          }`}
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {check.status === "checking" && (
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          )}
          {check.status === "valid" && (
            <CheckCircle2 className="w-5 h-5 text-green-500 animate-in zoom-in duration-300" />
          )}
          {check.status === "invalid" && (
            <AlertCircle className="w-5 h-5 text-red-500 animate-in shake duration-300" />
          )}
        </div>
      </div>
      {server === "starting" && (
        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
          <Loader2 className="w-3 h-3 animate-spin" />
          Starting local server...
        </p>
      )}
      {server === "failed" && (
        <p className="text-xs text-red-500 mt-1">
          The local server did not start.{" "}
          <button type="button" className="underline" onClick={onRetryServer}>
            Retry
          </button>
        </p>
      )}
      {check.status === "invalid" && (
        <p className="text-xs text-red-500 mt-1 animate-in fade-in slide-in-from-top-1">
          {check.error}
        </p>
      )}
      <p className="text-[11px] text-muted-foreground/60 leading-tight mt-2">
        {isTauri()
          ? "Choose with Browse, or enter the absolute path to your Fitbit export folder: the one that contains"
          : "Enter the absolute or relative path to your Fitbit export folder: the one that contains"}{" "}
        the <code>Global Export Data</code> folder (not the folder with the{" "}
        <code>heart_rate-*.json</code> files itself).
      </p>
    </div>
  );
}
