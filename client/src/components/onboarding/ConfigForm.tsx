import { useState, useEffect, useCallback } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { Command } from "@tauri-apps/plugin-shell";
import { appDataDir } from "@tauri-apps/api/path";
import { exists, readTextFile, writeTextFile, BaseDirectory, mkdir, remove } from "@tauri-apps/plugin-fs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CheckCircle2, AlertCircle, Search, Loader2, Trash2 } from "lucide-react";
import { useAppDispatch } from "../../store/store";
import { fetchHealthData, setIsProcessing } from "../../features/dashboard/dashboardSlice";

interface ConfigFormProps {
  onSuccess: () => void;
  submitLabel?: string;
}

export function ConfigForm({
  onSuccess,
  submitLabel = "Start Calculation",
}: ConfigFormProps) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    dob: "",
    gender: "",
    height: "",
    weight: "",
    data_path: "./data",
  });
  const [touched, setTouched] = useState({ dob: false, height: false, weight: false });
  const [pathStatus, setPathStatus] = useState<
    "idle" | "checking" | "valid" | "invalid"
  >("idle");
  const [pathError, setPathError] = useState("");

  useEffect(() => {
    const loadConfig = async () => {
      if (isTauri()) {
        try {
          const content = await readTextFile("session_config.json", { baseDir: BaseDirectory.AppData });
          const data = JSON.parse(content);
          if (data && Object.keys(data).length > 0) {
            setFormData((prev) => ({
              ...prev,
              dob: data.dob || prev.dob,
              gender: data.gender || prev.gender,
              height: data.height ? String(data.height) : prev.height,
              weight: data.weight ? String(data.weight) : prev.weight,
              data_path: data.data_path || prev.data_path,
            }));
            if (data.data_path) {
              setPathStatus("idle");
            }
          }
        } catch {
          // Normal on first run if file doesn't exist
        }
      } else {
        // Fetch saved configuration on mount for web
        fetch("http://localhost:8000/api/config")
          .then((res) => res.json())
          .then((data) => {
            if (data && Object.keys(data).length > 0) {
              setFormData((prev) => ({
                ...prev,
                dob: data.dob || prev.dob,
                gender: data.gender || prev.gender,
                height: data.height ? String(data.height) : prev.height,
                weight: data.weight ? String(data.weight) : prev.weight,
                data_path: data.data_path || prev.data_path,
              }));
              if (data.data_path) {
                 setPathStatus("idle");
              }
            }
          })
          .catch((err) => console.error("Could not fetch config:", err));
      }
    };
    loadConfig();
  }, []);

  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const firstFile = files[0];
      const relativePath = (
        firstFile as unknown as { webkitRelativePath: string }
      ).webkitRelativePath;
      if (relativePath) {
        const folderName = relativePath.split("/")[0];
        setFormData({ ...formData, data_path: `./${folderName}` });
        setPathStatus("idle");
      }
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
        if (selectedPath && typeof selectedPath === "string") {
          setFormData({ ...formData, data_path: selectedPath });
          setPathStatus("idle");
        }
      } catch (err) {
        console.error("Failed to open Tauri dialog:", err);
      }
    } else {
      // Fallback for web mode
      document.getElementById("folder-picker")?.click();
    }
  };

  const checkPath = useCallback(async (pathToCheck: string) => {
    if (!pathToCheck.trim()) {
      setPathStatus("idle");
      return;
    }
    setPathStatus("checking");

    if (isTauri()) {
      try {
        const isValid = await exists(pathToCheck.trim());
        if (isValid) {
          setPathStatus("valid");
          setPathError("");
        } else {
          setPathStatus("invalid");
          setPathError("Directory not found on local filesystem.");
        }
      } catch {
        setPathStatus("invalid");
        setPathError("Impossibile accedere al direttorio nativamente.");
      }
    } else {
      try {
        const resp = await fetch(
          `http://localhost:8000/api/check-path?path=${encodeURIComponent(pathToCheck.trim())}`,
        );
        const data = await resp.json();
        if (data.valid) {
          setPathStatus("valid");
          setPathError("");
        } else {
          setPathStatus("invalid");
          setPathError(data.reason);
        }
      } catch {
        setPathStatus("invalid");
        setPathError("Docker API server unreachable.");
      }
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      checkPath(formData.data_path);
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.data_path, checkPath]);

  const dispatch = useAppDispatch();

  const handleClearData = async () => {
    let isConfirmed = false;
    if (isTauri()) {
        const { confirm } = await import("@tauri-apps/plugin-dialog");
        isConfirmed = await confirm("Are you sure you want to delete all configuration and health data? This cannot be undone.", { title: 'FitStats - Factory Reset', kind: 'warning' });
    } else {
        isConfirmed = window.confirm("Are you sure you want to delete all configuration and health data? This cannot be undone.");
    }
    
    if (!isConfirmed) return;
    
    setLoading(true);
    try {
      if (isTauri()) {
        try { await remove("session_config.json", { baseDir: BaseDirectory.AppData }); } catch { /* ignore */ }
        try { await remove("dashboard_data.json", { baseDir: BaseDirectory.AppData }); } catch { /* ignore */ }
      } else {
        await fetch("http://localhost:8000/api/clear", { method: "DELETE" });
      }
      
      setFormData({ dob: "", gender: "", height: "", weight: "", data_path: "./data" });
      setPathStatus("idle");
      // Calling fetchHealthData will reload empty state causing NoDataState to re-render in Dashboard
      dispatch(fetchHealthData());
      alert("All application data has been successfully deleted.");
    } catch (e) {
      console.error("Error clearing data:", e);
      alert("Failed to clear data.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Basic Sanitization & Validation
    const heightVal = parseInt(formData.height);
    const weightVal = parseFloat(formData.weight);
    const pathVal = formData.data_path.trim();

    if (!formData.dob) {
      alert("Please enter a valid Date of Birth");
      return;
    }
    if (isNaN(heightVal) || heightVal < 50 || heightVal > 250) {
      alert("Please enter a valid height (50-250 cm)");
      return;
    }
    if (isNaN(weightVal) || weightVal < 20 || weightVal > 300) {
      alert("Please enter a valid weight (20-300 kg)");
      return;
    }
    if (!pathVal) {
      alert("Datastore path is required");
      return;
    }

    setLoading(true);
    dispatch(setIsProcessing(true));

    if (isTauri()) {
      try {
        const outDir = await appDataDir();
        
        // Save to native config
        try {
          await mkdir("", { baseDir: BaseDirectory.AppData, recursive: true }).catch(() => {});
          await writeTextFile("session_config.json", JSON.stringify(formData), { baseDir: BaseDirectory.AppData });
        } catch (e) {
          console.warn("Could not save config to appDataDir", e);
        }
        
        const cmd = Command.sidecar("bin/fitstats-engine", [
          "--dob", formData.dob,
          "--gender", formData.gender,
          "--height", String(heightVal),
          "--weight", String(weightVal),
          "--data-dir", pathVal,
          "--out-dir", outDir
        ]);
        
        // Close form instantly and let it run in background closure
        onSuccess();
        
        cmd.execute().then(output => {
           dispatch(setIsProcessing(false));
           if (output.code === 0) {
             dispatch(fetchHealthData());
           } else {
             console.error("Sidecar execution failed:", output.stderr);
             alert("Error executing ETL: " + output.stderr);
           }
        }).catch(err => {
           dispatch(setIsProcessing(false));
           console.error("Tauri sidecar invocation exception:", err);
           alert("Failed to spawn background engine.");
        });

      } catch (err) {
        dispatch(setIsProcessing(false));
        setLoading(false);
        console.error("Tauri sidecar invocation exception:", err);
      }
    } else {
      try {
        const resp = await fetch(`http://localhost:8000/api/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            dob: formData.dob,
            gender: formData.gender,
            height: heightVal,
            weight: weightVal,
            data_path: pathVal,
          }),
        });

        if (!resp.ok) {
          console.error("Failed to start processing");
          dispatch(setIsProcessing(false));
          setLoading(false);
          alert("Error starting calculation on the server.");
        } else {
          // Close form instantly and listen in background
          onSuccess();
          
          const ws = new WebSocket("ws://localhost:8000/ws/status");
          
          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (data.event === "etl_finished") {
                dispatch(setIsProcessing(false));
                ws.close();
                if (data.status === "success") {
                  dispatch(fetchHealthData());
                } else {
                  alert("Error during ETL: " + data.message);
                }
              }
            } catch (e) {
              console.error("Error parsing WS message:", e);
            }
          };
          
          ws.onerror = (error) => {
             console.error("WebSocket error:", error);
             dispatch(setIsProcessing(false));
             ws.close();
             alert("WebSocket disconnected unexpectedly.");
          };
        }
      } catch (err) {
        console.error(err);
        dispatch(setIsProcessing(false));
        setLoading(false);
        alert("Failed to connect to the local server.");
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-left">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2 text-left">
          <Label htmlFor="dob">Date of Birth</Label>
          <Input
            id="dob"
            type="date"
            required
            value={formData.dob}
            onChange={(e) => {
              setFormData({ ...formData, dob: e.target.value });
              setTouched({ ...touched, dob: true });
            }}
            className={`h-12 text-lg transition-all duration-300 ${!formData.dob ? "text-muted-foreground/40" : ""}`}
            placeholder="YYYY-MM-DD"
          />
        </div>
        <div className="space-y-2 text-left">
          <Label htmlFor="height">Height (cm)</Label>
          <Input
            id="height"
            type="number"
            min="50"
            max="250"
            required
            placeholder="e.g. 175 cm"
            value={formData.height}
            onFocus={(e) => e.target.select()}
            onChange={(e) => {
              setFormData({ ...formData, height: e.target.value });
              setTouched({ ...touched, height: true });
            }}
            className={`h-12 text-lg transition-all duration-300 ${!formData.height ? "text-muted-foreground/40" : ""}`}
          />
        </div>
        <div className="space-y-2 text-left">
          <Label htmlFor="weight">Weight (kg)</Label>
          <Input
            id="weight"
            type="number"
            min="20"
            max="300"
            step="0.1"
            required
            placeholder="e.g. 70.0 kg"
            value={formData.weight}
            onFocus={(e) => e.target.select()}
            onChange={(e) => {
              setFormData({ ...formData, weight: e.target.value });
              setTouched({ ...touched, weight: true });
            }}
            className={`h-12 text-lg transition-all duration-300 ${!formData.weight ? "text-muted-foreground/40" : ""}`}
          />
        </div>
      </div>

      <div className="space-y-2 text-left">
        <Label htmlFor="gender">Gender</Label>
        <Select
          value={formData.gender}
          onValueChange={(value) => setFormData({ ...formData, gender: value })}
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
            placeholder="./data"
            value={formData.data_path}
            onFocus={(e) => e.target.select()}
            onChange={(e) => {
              setFormData({ ...formData, data_path: e.target.value });
              setPathStatus("idle");
            }}
            className={`h-12 pr-24 transition-colors ${
              pathStatus === "valid"
                ? "border-green-500/50 bg-green-500/5"
                : pathStatus === "invalid"
                  ? "border-red-500/50 bg-red-500/5"
                  : ""
            }`}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {pathStatus === "checking" && (
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            )}
            {pathStatus === "valid" && (
              <CheckCircle2 className="w-5 h-5 text-green-500 animate-in zoom-in duration-300" />
            )}
            {pathStatus === "invalid" && (
              <AlertCircle className="w-5 h-5 text-red-500 animate-in shake duration-300" />
            )}
          </div>
        </div>
        {pathStatus === "invalid" && (
          <p className="text-xs text-red-500 mt-1 animate-in fade-in slide-in-from-top-1">
            {pathError}
          </p>
        )}
        <p className="text-[11px] text-muted-foreground/60 leading-tight mt-2">
          Enter the absolute or relative path to your Fitbit export folder.
          Usually contains files like <code>heart_rate-YYYY-MM-DD.json</code>.
        </p>
      </div>

      <div className="pt-6 flex gap-3">
        <Button
          type="button"
          variant="outline"
          className="h-12 w-12 p-0 flex-shrink-0 text-red-500 hover:text-red-600 hover:bg-red-500/10 border-red-500/20"
          onClick={handleClearData}
          disabled={loading}
          title="Factory Reset: Clear all data"
        >
          <Trash2 className="w-5 h-5" />
        </Button>
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
