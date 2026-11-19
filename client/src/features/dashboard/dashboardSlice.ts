import {
  createSlice,
  createAsyncThunk,
  type PayloadAction,
} from "@reduxjs/toolkit";
import type { HealthRecord, DateRange } from "@/types/health";
import { subMonths, parseISO, format } from "date-fns";
import { isTauri } from "@tauri-apps/api/core";
import { readTextFile, exists, BaseDirectory } from "@tauri-apps/plugin-fs";

interface DashboardState {
  data: HealthRecord[];
  filteredData: HealthRecord[];
  dateRange: DateRange | null;
  minDataDate: string;
  maxDataDate: string;
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
}

const initialState: DashboardState = {
  data: [],
  filteredData: [],
  dateRange: null,
  minDataDate: "",
  maxDataDate: "",
  status: "idle",
  error: null,
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

/** Reads the dashboard data. A missing file is an empty result; any other failure throws. */
async function readDashboardData(): Promise<HealthRecord[]> {
  if (isTauri()) {
    if (!(await exists("dashboard_data.json", { baseDir: BaseDirectory.AppData }))) {
      console.warn("dashboard_data.json not found locally (normal on first run)");
      return [];
    }
    let content: string;
    try {
      content = await readTextFile("dashboard_data.json", { baseDir: BaseDirectory.AppData });
    } catch (e) {
      console.error("Error reading dashboard_data.json:", e);
      throw new Error("Could not read dashboard_data.json from the app data folder.");
    }
    return parseDashboardData(content);
  }

  let response: Response;
  try {
    response = await fetch("/dashboard_data.json");
  } catch (e) {
    console.error("Error fetching dashboard data:", e);
    throw new Error("Could not load dashboard_data.json (network error).");
  }
  // A dev server answers a missing file with its HTML page instead of a 404.
  const isHtml = (response.headers.get("content-type") ?? "").includes("text/html");
  if (response.status === 404 || (response.ok && isHtml)) {
    console.warn("dashboard_data.json not found (normal on first run)");
    return [];
  }
  if (!response.ok) {
    throw new Error(`Could not load dashboard_data.json (HTTP ${response.status}).`);
  }
  return parseDashboardData(await response.text());
}

export const fetchHealthData = createAsyncThunk<HealthRecord[], { force?: boolean } | undefined>(
  "dashboard/fetchHealthData",
  async () => readDashboardData(),
  {
    // --- CACHING LOGIC ---
    // Skip the call when data is already loaded or loading, unless the caller
    // passes `force` (after a finished ETL run or a reset the file has changed).
    condition: (arg, { getState }) => {
      if (arg?.force) return true;
      const { dashboard } = getState() as { dashboard: DashboardState };

      if (dashboard.status === "succeeded" || dashboard.status === "loading") {
        return false;
      }
      return true;
    },
  }
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
      .addCase(fetchHealthData.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(fetchHealthData.fulfilled, (state, action) => {
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
