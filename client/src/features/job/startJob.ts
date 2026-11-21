import type { AppDispatch } from "@/store/store";
import { apiFetch } from "@/lib/api";
import { snapshotReceived, type JobSnapshot } from "./jobSlice";

export interface StartBody {
  dob: string;
  gender: string;
  height: number;
  weight: number;
  data_path: string;
}

export type StartResult =
  | { kind: "started" }
  /** A run was already in progress; the store now shows it. */
  | { kind: "busy" }
  /** The server answered with another status (for example 502 while it restarts). */
  | { kind: "failed"; status: number };

/**
 * Asks the server to start a calculation and puts the job it answers with in
 * the store. Throws if the server cannot be reached.
 */
export async function startJob(dispatch: AppDispatch, body: StartBody): Promise<StartResult> {
  const resp = await apiFetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (resp.status === 202) {
    dispatch(snapshotReceived((await resp.json()) as JobSnapshot));
    return { kind: "started" };
  }
  if (resp.status === 409) {
    const data = (await resp.json().catch(() => null)) as { job?: JobSnapshot } | null;
    if (data?.job) dispatch(snapshotReceived(data.job));
    return { kind: "busy" };
  }
  console.error("Failed to start processing", resp.status);
  return { kind: "failed", status: resp.status };
}
