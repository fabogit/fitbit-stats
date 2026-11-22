import {
  createSlice,
  createAsyncThunk,
  createSelector,
  type PayloadAction,
} from "@reduxjs/toolkit";
import type { HealthRecord, DateRange } from "@/types/health";
import { subMonths, parseISO, format } from "date-fns";
import { apiFetch } from "@/lib/api";

interface DashboardState {
  data: HealthRecord[];
  /** The period shown; null while there is no data. The filtered records are derived (selectFilteredData). */
  dateRange: DateRange | null;
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
  /** The load whose result counts: a slower, older load must not overwrite a newer one. */
  requestId: string | null;
}

const initialState: DashboardState = {
  data: [],
  dateRange: null,
  status: "idle",
  error: null,
  requestId: null,
};

/** Parses the content of dashboard_data.json; anything but a JSON array is an error. */
function parseDashboardData(text: string): HealthRecord[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("dashboard_data.json is not valid JSON. Recalculate your data to regenerate it.");
  }
  if (!Array.isArray(parsed)) {
    throw new Error("dashboard_data.json has an unexpected format. Recalculate your data to regenerate it.");
  }
  return parsed as HealthRecord[];
}

/**
 * Reads the dashboard data from the API, the same way on desktop and web.
 * "No data yet" is an empty array from the server; every other failure throws.
 */
async function readDashboardData(): Promise<HealthRecord[]> {
  let response: Response;
  try {
    response = await apiFetch("/api/data");
  } catch (e) {
    console.error("Error fetching dashboard data:", e);
    throw new Error("Could not load the dashboard data: the local server did not answer.");
  }
  if (!response.ok) {
    throw new Error(`Could not load the dashboard data (HTTP ${response.status}).`);
  }
  // An answer that is not JSON (a proxy or a web server in the way) is not "no data".
  if (!(response.headers.get("content-type") ?? "").includes("json")) {
    throw new Error("Could not load the dashboard data: the server did not answer with JSON.");
  }
  return parseDashboardData(await response.text());
}

/** Loads the dashboard data. Every dispatch reads it again; callers decide when. */
export const fetchHealthData = createAsyncThunk<HealthRecord[]>(
  "dashboard/fetchHealthData",
  async () => readDashboardData()
);

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {
    setDateRange(state, action: PayloadAction<DateRange>) {
      state.dateRange = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHealthData.pending, (state, action) => {
        state.status = "loading";
        state.error = null;
        state.requestId = action.meta.requestId;
      })
      .addCase(fetchHealthData.fulfilled, (state, action) => {
        if (action.meta.requestId !== state.requestId) return;
        const records = action.payload;
        state.status = "succeeded";
        state.error = null;
        state.data = records;

        if (records.length > 0) {
          const endDate = records[records.length - 1].date;
          let startDate = format(subMonths(parseISO(endDate), 3), "yyyy-MM-dd");
          if (startDate < records[0].date) {
            startDate = records[0].date;
          }
          state.dateRange = { start: startDate, end: endDate };
        } else {
          // Empty result (e.g. after a reset): drop everything shown before.
          state.dateRange = null;
        }
      })
      .addCase(fetchHealthData.rejected, (state, action) => {
        if (action.meta.requestId !== state.requestId) return;
        // Never keep showing data that could not be refreshed.
        state.status = "failed";
        state.error = action.error.message || "Unknown error";
        state.data = [];
        state.dateRange = null;
      });
  },
});

export const { setDateRange } = dashboardSlice.actions;

type DashboardRoot = { dashboard: DashboardState };

export const selectData = (state: DashboardRoot) => state.dashboard.data;
export const selectDateRange = (state: DashboardRoot) => state.dashboard.dateRange;
export const selectDashboardStatus = (state: DashboardRoot) => state.dashboard.status;
export const selectDashboardError = (state: DashboardRoot) => state.dashboard.error;
export const selectHasData = (state: DashboardRoot) => state.dashboard.data.length > 0;

/**
 * The records inside the selected period. Computed again only when the data or
 * the period changes. A null period happens only with no data (or before the
 * first load), and then there is nothing to show.
 */
export const selectFilteredData = createSelector(
  [selectData, selectDateRange],
  (data, range) => (range ? data.filter((d) => d.date >= range.start && d.date <= range.end) : [])
);

/** Whether the selected period contains at least one record. */
export const selectHasFilteredData = (state: DashboardRoot) => selectFilteredData(state).length > 0;

/** First and last date of the loaded data (the data comes sorted by date); empty strings without data. */
export const selectDateBounds = createSelector([selectData], (data) => ({
  min: data.length > 0 ? data[0].date : "",
  max: data.length > 0 ? data[data.length - 1].date : "",
}));

export default dashboardSlice.reducer;
