import { createListenerMiddleware } from "@reduxjs/toolkit";
import { fetchHealthData } from "@/features/dashboard/dashboardSlice";
import { runDataRequested, snapshotReceived, type JobRootState } from "./jobSlice";

/** Reloads the dashboard data when a run finishes that it has not loaded yet. */
export const jobListener = createListenerMiddleware();

jobListener.startListening({
  actionCreator: snapshotReceived,
  effect: (action, api) => {
    const snapshot = action.payload;
    const { loadedRunId } = (api.getState() as JobRootState).job;
    if (snapshot.state !== "finished" || !snapshot.id || snapshot.id === loadedRunId) return;
    api.dispatch(runDataRequested(snapshot.id));
    void api.dispatch(fetchHealthData({ force: true }));
  },
});
