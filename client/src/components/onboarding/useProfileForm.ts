import { useCallback, useEffect, useRef, useState } from "react";
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

/** The saved value of each field, where there is one that can be used. */
function savedValues(data: SavedConfig): Partial<ProfileValues> {
  const saved: Partial<ProfileValues> = {};
  if (data.dob) saved.dob = data.dob;
  if (data.gender === "male" || data.gender === "female") saved.gender = data.gender;
  if (data.height) saved.height = String(data.height);
  if (data.weight) saved.weight = String(data.weight);
  // A relative path saved by an older desktop version cannot be resolved
  // there: leave the field empty instead.
  if (data.data_path && !isDesktopRelativePath(data.data_path)) saved.data_path = data.data_path;
  return saved;
}

/**
 * The values of the profile form: waits for the local server (a cold start
 * takes seconds), then fills the form with the saved configuration. The saved
 * configuration only fills fields the user has not touched: on a slow start it
 * arrives after they began typing.
 */
export function useProfileForm(): ProfileForm {
  const [values, setValues] = useState<ProfileValues>(emptyValues);
  const [server, setServer] = useState<ServerState>("starting");
  const [attempt, setAttempt] = useState(0);
  const modified = useRef(new Set<keyof ProfileValues>());

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
        if (!data) return;
        const fill = savedValues(data);
        for (const key of modified.current) delete fill[key];
        // Applied on top of whatever the user has typed so far.
        setValues((prev) => ({ ...prev, ...fill }));
      })
      .catch((err) => {
        if (!controller.signal.aborted) console.error("Could not fetch config:", err);
      });
    return () => controller.abort();
  }, [server]);

  const set = useCallback((patch: Partial<ProfileValues>) => {
    for (const key of Object.keys(patch)) modified.current.add(key as keyof ProfileValues);
    setValues((prev) => ({ ...prev, ...patch }));
  }, []);
  const clear = useCallback(() => {
    // A configuration still on its way is the one that was just deleted.
    for (const key of Object.keys(emptyValues())) modified.current.add(key as keyof ProfileValues);
    setValues(emptyValues());
  }, []);
  const retryServer = useCallback(() => {
    setServer("starting");
    setAttempt((n) => n + 1);
  }, []);

  return { values, set, clear, server, retryServer };
}
