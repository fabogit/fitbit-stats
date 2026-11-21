import { useCallback, useEffect, useState } from "react";
import { apiFetch, waitForServer } from "@/lib/api";
import { defaultDataPath, isDesktopRelativePath } from "./usePathCheck";

export type Gender = "" | "male" | "female";

export interface ProfileValues {
  dob: string;
  gender: Gender;
  /** Text of the field; `validateProfile` turns it into a number. */
  height: string;
  weight: string;
  data_path: string;
}

export type ServerState = "starting" | "ready" | "failed";

export interface ProfileForm {
  values: ProfileValues;
  set(patch: Partial<ProfileValues>): void;
  /** Empties the form, for after a reset. */
  clear(): void;
  server: ServerState;
  retryServer(): void;
}

const emptyValues = (): ProfileValues => ({
  dob: "",
  gender: "",
  height: "",
  weight: "",
  data_path: defaultDataPath(),
});

/** What GET /api/config answers; every field may be missing. */
interface SavedConfig {
  dob?: string;
  gender?: string;
  height?: number;
  weight?: number;
  data_path?: string;
}

function mergeConfig(prev: ProfileValues, data: SavedConfig): ProfileValues {
  return {
    dob: data.dob || prev.dob,
    gender: data.gender === "male" || data.gender === "female" ? data.gender : prev.gender,
    height: data.height ? String(data.height) : prev.height,
    weight: data.weight ? String(data.weight) : prev.weight,
    // A relative path saved by an older desktop version cannot be resolved
    // there: leave the field empty instead.
    data_path:
      data.data_path && !isDesktopRelativePath(data.data_path) ? data.data_path : prev.data_path,
  };
}

/**
 * The values of the profile form: waits for the local server (a cold start
 * takes seconds), then fills the form with the saved configuration.
 */
export function useProfileForm(): ProfileForm {
  const [values, setValues] = useState<ProfileValues>(emptyValues);
  const [server, setServer] = useState<ServerState>("starting");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    waitForServer(controller.signal).then((ok) => {
      if (!controller.signal.aborted) setServer(ok ? "ready" : "failed");
    });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (server !== "ready") return;
    const controller = new AbortController();
    apiFetch("/api/config", { signal: controller.signal })
      .then((res) => res.json())
      .then((data: SavedConfig | null) => {
        if (data && Object.keys(data).length > 0) setValues((prev) => mergeConfig(prev, data));
      })
      .catch((err) => {
        if (!controller.signal.aborted) console.error("Could not fetch config:", err);
      });
    return () => controller.abort();
  }, [server]);

  const set = useCallback((patch: Partial<ProfileValues>) => {
    setValues((prev) => ({ ...prev, ...patch }));
  }, []);
  const clear = useCallback(() => setValues(emptyValues()), []);
  const retryServer = useCallback(() => {
    setServer("starting");
    setAttempt((n) => n + 1);
  }, []);

  return { values, set, clear, server, retryServer };
}
