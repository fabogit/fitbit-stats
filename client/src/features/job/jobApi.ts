import type { AppDispatch } from "@/store/store";
import { apiFetch } from "@/lib/api";
import { snapshotReceived, type JobSnapshot } from "./jobSlice";

/** Reads GET /api/status into the store. Throws if the server cannot be reached. */
export async function loadJobStatus(dispatch: AppDispatch): Promise<void> {
  const resp = await apiFetch("/api/status");
  if (!resp.ok) throw new Error(`Status request failed (HTTP ${resp.status})`);
  dispatch(snapshotReceived((await resp.json()) as JobSnapshot));
}
