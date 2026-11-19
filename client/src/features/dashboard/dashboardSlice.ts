import {
  createSlice,
  createAsyncThunk,
  type PayloadAction,
} from "@reduxjs/toolkit";
import type { HealthRecord, DateRange } from "@/types/health";
import { subMonths, parseISO, format } from "date-fns";
import { apiFetch } from "@/lib/api";

interface DashboardState {
  data: HealthRecord[];
  filteredData: HealthRecord[];
  dateRange: DateRange | null;
  minDataDate: string;
  maxDataDate: string;
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
  /** The load whose result counts: a slower, older load must not overwrite a newer one. */
  requestId: string | null;
}

const initialState: DashboardState = {
  data: [],
  filteredData: [],
  dateRange: null,
  minDataDate: "",
  maxDataDate: "",
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
      state.filteredData = state.data.filter(
        (d) => d.date >= action.payload.start && d.date <= action.payload.end
      );
    },
    resetFilter(state) {
      if (state.data.length > 0) {
        const start = state.data[0].date;
        const end = state.data[state.data.length - 1].date;
        state.dateRange = { start, end };
        state.filteredData = state.data;
      }
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
          const firstRecord = records[0];
          const lastRecord = records[records.length - 1];

          state.minDataDate = firstRecord.date;
          state.maxDataDate = lastRecord.date;

          const endDate = lastRecord.date;

          const endObj = parseISO(endDate);
          const startObj = subMonths(endObj, 3);
          let startDate = format(startObj, "yyyy-MM-dd");

          if (startDate < firstRecord.date) {
            startDate = firstRecord.date;
          }

          state.dateRange = { start: startDate, end: endDate };
          state.filteredData = records.filter(
            (d) => d.date >= startDate && d.date <= endDate
          );
        } else {
          // Empty result (e.g. after a reset): drop everything shown before.
          state.filteredData = [];
          state.dateRange = null;
          state.minDataDate = "";
          state.maxDataDate = "";
        }
      })
      .addCase(fetchHealthData.rejected, (state, action) => {
        if (action.meta.requestId !== state.requestId) return;
        // Never keep showing data that could not be refreshed.
        state.status = "failed";
        state.error = action.error.message || "Unknown error";
        state.data = [];
        state.filteredData = [];
        state.dateRange = null;
        state.minDataDate = "";
        state.maxDataDate = "";
      });
  },
});

export const { setDateRange, resetFilter } = dashboardSlice.actions;

export const selectFilteredData = (state: { dashboard: DashboardState }) => state.dashboard.filteredData;
export const selectDashboardStatus = (state: { dashboard: DashboardState }) => state.dashboard.status;

export default dashboardSlice.reducer;
