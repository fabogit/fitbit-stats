import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

/** A file the last run skipped (file name only) and why. */
export interface EtlWarning {
  file: string;
  reason: string;
}

export type JobState = "idle" | "running" | "finished" | "error";

/** The status of the ETL job, as the server sends it (GET /api/status and the WebSocket). */
export interface JobSnapshot {
  /** Random per server process: a different value means the server restarted. */
  instance: string;
  /** Grows with every change within one `instance`. */
  seq: number;
  /** Id of the last known run; null if there is none. */
  id: string | null;
  state: JobState;
  progress: number;
  step: string;
  started_at: string | null;
  finished_at: string | null;
  /** Outcome or error of the run; never a folder path. */
  message: string | null;
  warnings: EtlWarning[];
}

export interface JobSliceState {
  /** Latest snapshot; null until the server has been heard from. */
  snapshot: JobSnapshot | null;
  /** The finished run whose data the dashboard has loaded (or is loading). */
  loadedRunId: string | null;
}

export interface JobRootState {
  job: JobSliceState;
}

const initialState: JobSliceState = { snapshot: null, loadedRunId: null };

const EMPTY_WARNINGS: EtlWarning[] = [];

const jobSlice = createSlice({
  name: "job",
  initialState,
  reducers: {
    /**
     * Takes a snapshot from the server, unless a newer one of the same server
     * process was already taken (snapshots can arrive out of order: the
     * response to POST /api/start, a status read, a WebSocket message).
     */
    snapshotReceived(state, action: PayloadAction<JobSnapshot>) {
      const next = action.payload;
      const current = state.snapshot;
      if (current && current.instance === next.instance && next.seq < current.seq) return;
      // The first snapshot is the baseline: a run that finished before the
      // page opened is what the first data load reads anyway.
      if (current === null) {
        state.loadedRunId = next.state === "finished" ? next.id : null;
      }
      state.snapshot = next;
    },
    /** The data of this finished run is being loaded. */
    runDataRequested(state, action: PayloadAction<string>) {
      state.loadedRunId = action.payload;
    },
  },
});

export const { snapshotReceived, runDataRequested } = jobSlice.actions;

export const selectIsRunning = (state: JobRootState) => state.job.snapshot?.state === "running";
export const selectProgress = (state: JobRootState) => state.job.snapshot?.progress ?? 0;
export const selectStep = (state: JobRootState) => state.job.snapshot?.step ?? "";
export const selectWarnings = (state: JobRootState) =>
  state.job.snapshot?.warnings ?? EMPTY_WARNINGS;
/** Message of the last run when it failed, otherwise null. */
export const selectFailureMessage = (state: JobRootState) => {
  const snapshot = state.job.snapshot;
  return snapshot?.state === "error" ? (snapshot.message ?? "Unknown error") : null;
};

export default jobSlice.reducer;
