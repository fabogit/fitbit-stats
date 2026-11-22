import { useEffect, useState } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { apiFetch } from "@/lib/api";

export type PathStatus = "idle" | "checking" | "valid" | "invalid";

export interface PathCheck {
  status: PathStatus;
  error: string | null;
}

// The packaged desktop server resolves relative paths against its own
// temporary extraction folder, so there the folder must be absolute.
export const RELATIVE_PATH_ERROR = "Use an absolute path or Browse.";
const UNREACHABLE_ERROR = "API server unreachable. Make sure the backend is running.";

const isAbsolutePath = (p: string) => /^([/\\]|[A-Za-z]:[/\\])/.test(p);

export const isDesktopRelativePath = (p: string) =>
  isTauri() && p.trim() !== "" && !isAbsolutePath(p.trim());

export const defaultDataPath = () => (isTauri() ? "" : "./data");

interface CheckResult extends PathCheck {
  /** The path this result is about. */
  path: string;
}

/**
 * Checks `path` with the server `delayMs` after the last change, only while
 * `enabled`. The result of an older path is never shown for a newer one: the
 * status is "idle" until the new check has run, and a request still in flight
 * for an old path is cancelled.
 */
export function usePathCheck(path: string, enabled: boolean, delayMs = 500): PathCheck {
  const [result, setResult] = useState<CheckResult | null>(null);

  useEffect(() => {
    const target = path.trim();
    if (!enabled || !target) return;
    const controller = new AbortController();
    const { signal } = controller;
    const timer = setTimeout(async () => {
      if (isDesktopRelativePath(target)) {
        setResult({ path, status: "invalid", error: RELATIVE_PATH_ERROR });
        return;
      }
      setResult({ path, status: "checking", error: null });
      try {
        const resp = await apiFetch(`/api/check-path?path=${encodeURIComponent(target)}`, {
          signal,
        });
        const data = await resp.json();
        if (signal.aborted) return;
        setResult(
          data.valid
            ? { path, status: "valid", error: null }
            : { path, status: "invalid", error: data.reason },
        );
      } catch {
        // A cancelled request is not a failure: a newer check replaces it.
        if (!signal.aborted) setResult({ path, status: "invalid", error: UNREACHABLE_ERROR });
      }
    }, delayMs);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [path, enabled, delayMs]);

  if (!enabled || !path.trim() || result?.path !== path) return { status: "idle", error: null };
  return { status: result.status, error: result.error };
}
