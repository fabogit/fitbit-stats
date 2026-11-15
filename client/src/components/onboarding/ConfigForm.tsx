import { useState, useEffect, useCallback, useRef } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
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
import { fetchHealthData, setIsProcessing, setEtlProgress } from "../../features/dashboard/dashboardSlice";
import { apiFetch, openStatusSocket, waitForServer } from "@/lib/api";
import {
  HEIGHT_CM_MIN,
  HEIGHT_CM_MAX,
  WEIGHT_KG_MIN,
  WEIGHT_KG_MAX,
  dobBounds,
} from "@/lib/biometrics";

interface ConfigFormProps {
  onSuccess: () => void;
  submitLabel?: string;
}

export function ConfigForm({
  onSuccess,
  submitLabel = "Start Calculation",
}: ConfigFormProps) {
  const selectOnClick = useRef(false);
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
  const [serverState, setServerState] = useState<
    "starting" | "ready" | "failed"
  >("starting");
  const [serverAttempt, setServerAttempt] = useState(0);

  // Wait for the local server before talking to it: a cold start takes seconds.
  useEffect(() => {
    const controller = new AbortController();
    setServerState("starting");
    waitForServer(controller.signal).then((ok) => {
      if (!controller.signal.aborted) setServerState(ok ? "ready" : "failed");
    });
    return () => controller.abort();
  }, [serverAttempt]);

  useEffect(() => {
    if (serverState !== "ready") return;
    const loadConfig = async () => {
      apiFetch("/api/config")
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
    };
    loadConfig();
  }, [serverState]);

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

    try {
      const resp = await apiFetch(
        `/api/check-path?path=${encodeURIComponent(pathToCheck.trim())}`,
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
      setPathError("API server unreachable. Make sure the backend is running.");
    }
  }, []);

  useEffect(() => {
    if (serverState !== "ready") return;
    const timer = setTimeout(() => {
      checkPath(formData.data_path);
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.data_path, checkPath, serverState]);

  const dispatch = useAppDispatch();

  const handleClearData = async () => {
    const isConfirmed = window.confirm("Are you sure you want to delete all configuration and health data? This cannot be undone.");
    if (!isConfirmed) return;
    
    setLoading(true);
    try {
      await apiFetch("/api/clear", { method: "DELETE" });
      
      setFormData({ dob: "", gender: "", height: "", weight: "", data_path: "./data" });
      setPathStatus("idle");
      // Calling fetchHealthData will reload empty state causing NoDataState to re-render in Dashboard
      dispatch(fetchHealthData({ force: true }));
      alert("All application data has been successfully deleted.");
    } catch (e) {
      console.error("Error clearing data:", e);
      alert("Failed to clear data.");
    } finally {
      setLoading(false);
    }
  };

  const { min: dobMin, max: dobMax } = dobBounds();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Basic Sanitization & Validation
    const heightVal = parseInt(formData.height);
    const weightVal = parseFloat(formData.weight);
    const pathVal = formData.data_path.trim();

    if (!formData.dob || formData.dob < dobMin || formData.dob > dobMax) {
      alert("Please enter a valid Date of Birth");
      return;
    }
    if (formData.gender !== "male" && formData.gender !== "female") {
      alert("Please select a gender");
      return;
    }
    if (isNaN(heightVal) || heightVal < HEIGHT_CM_MIN || heightVal > HEIGHT_CM_MAX) {
      alert(`Please enter a valid height (${HEIGHT_CM_MIN}-${HEIGHT_CM_MAX} cm)`);
      return;
    }
    if (isNaN(weightVal) || weightVal < WEIGHT_KG_MIN || weightVal > WEIGHT_KG_MAX) {
      alert(`Please enter a valid weight (${WEIGHT_KG_MIN}-${WEIGHT_KG_MAX} kg)`);
      return;
    }
    if (!pathVal) {
      alert("Datastore path is required");
      return;
    }

    setLoading(true);
    dispatch(setIsProcessing(true));

    let ws: WebSocket | null = null;
    try {
      // Open the status channel first: events broadcast before a client is
      // connected are lost, so the ETL must not start until the socket is open.
      const socket = await openStatusSocket();
      ws = socket;
      await new Promise<void>((resolve, reject) => {
        socket.onopen = () => resolve();
        socket.onerror = () => reject(new Error("WebSocket connection failed"));
      });

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "etl_progress") {
            dispatch(setEtlProgress({ progress: data.progress, step: data.step }));
          } else if (data.event === "etl_finished") {
            dispatch(setIsProcessing(false));
            socket.close();
            if (data.status === "success") {
              dispatch(fetchHealthData({ force: true }));
            } else {
              alert("Error during ETL: " + data.message);
            }
          }
        } catch (e) {
          console.error("Error parsing WS message:", e);
        }
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        dispatch(setIsProcessing(false));
        socket.close();
        alert("WebSocket disconnected unexpectedly.");
      };

      const resp = await apiFetch("/api/start", {
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
        socket.onerror = null;
        socket.close();
        dispatch(setIsProcessing(false));
        setLoading(false);
        alert("Error starting calculation on the server.");
      } else {
        // Close form instantly; the already-open socket keeps listening
        onSuccess();
      }
    } catch (err) {
      console.error(err);
      if (ws) {
        ws.onerror = null;
        ws.close();
      }
      dispatch(setIsProcessing(false));
      setLoading(false);
      alert("Failed to connect to the local server.");
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
            min={dobMin}
            max={dobMax}
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
            min={HEIGHT_CM_MIN}
            max={HEIGHT_CM_MAX}
            step="1"
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
            min={WEIGHT_KG_MIN}
            max={WEIGHT_KG_MAX}
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
          required
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
        {serverState === "starting" && (
          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            Starting local server...
          </p>
        )}
        {serverState === "failed" && (
          <p className="text-xs text-red-500 mt-1">
            The local server did not start.{" "}
            <button
              type="button"
              className="underline"
              onClick={() => setServerAttempt((n) => n + 1)}
            >
              Retry
            </button>
          </p>
        )}
        {pathStatus === "invalid" && (
          <p className="text-xs text-red-500 mt-1 animate-in fade-in slide-in-from-top-1">
            {pathError}
          </p>
        )}
        <p className="text-[11px] text-muted-foreground/60 leading-tight mt-2">
          Enter the absolute or relative path to your Fitbit export folder: the
          one that contains the <code>Global Export Data</code> folder (not the
          folder with the <code>heart_rate-*.json</code> files itself).
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
