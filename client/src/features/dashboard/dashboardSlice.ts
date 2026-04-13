import {
  createSlice,
  createAsyncThunk,
  type PayloadAction,
} from "@reduxjs/toolkit";
import type { HealthRecord, DateRange } from "@/types/health";
import { subMonths, parseISO, format } from "date-fns";
import { isTauri } from "@tauri-apps/api/core";
import { readTextFile, BaseDirectory } from "@tauri-apps/plugin-fs";

interface DashboardState {
  data: HealthRecord[];
  filteredData: HealthRecord[];
  dateRange: DateRange | null;
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
  isProcessing: boolean;
  etlProgress: number;
  etlStep: string;
}

const initialState: DashboardState = {
  data: [],
  filteredData: [],
  dateRange: null,
  status: "idle",
  error: null,
  isProcessing: false,
  etlProgress: 0,
  etlStep: "",
};

export const fetchHealthData = createAsyncThunk(
  "dashboard/fetchHealthData",
  async () => {
    try {
      if (isTauri()) {
        try {
          const content = await readTextFile("dashboard_data.json", { baseDir: BaseDirectory.AppData });
          return JSON.parse(content) as HealthRecord[];
        } catch (fileErr) {
          console.warn("dashboard_data.json not found locally. (Normal on first run)", fileErr);
          return [];
        }
      } else {
        const response = await fetch("/dashboard_data.json");
        if (response.status === 404) {
          console.warn("dashboard_data.json not found (normal on first run)");
          return [];
        }
        if (!response.ok) throw new Error("Failed to load dashboard data");
        return (await response.json()) as HealthRecord[];
      }
    } catch (e) {
      console.error("Error fetching dashboard data:", e);
      return []; // Return empty array instead of failing the state
    }
  },
  {
    // --- CACHING LOGIC ---
    condition: (_, { getState }) => {
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
    setIsProcessing(state, action: PayloadAction<boolean>) {
      state.isProcessing = action.payload;
      if (!action.payload) {
        state.etlProgress = 0;
        state.etlStep = "";
      }
    },
    setEtlProgress(state, action: PayloadAction<{ progress: number; step: string }>) {
      state.etlProgress = action.payload.progress;
      state.etlStep = action.payload.step;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHealthData.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchHealthData.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.data = action.payload;

        if (action.payload.length > 0) {
          const lastRecord = action.payload[action.payload.length - 1];
          const firstRecord = action.payload[0];

          const endDate = lastRecord.date;

          const endObj = parseISO(endDate);
          const startObj = subMonths(endObj, 3);
          let startDate = format(startObj, "yyyy-MM-dd");

          if (startDate < firstRecord.date) {
            startDate = firstRecord.date;
          }

          state.dateRange = { start: startDate, end: endDate };
          state.filteredData = action.payload.filter(
            (d) => d.date >= startDate && d.date <= endDate
          );
        }
      })
      .addCase(fetchHealthData.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message || "Unknown error";
      });
  },
});

export const { setDateRange, resetFilter, setIsProcessing, setEtlProgress } = dashboardSlice.actions;

export const selectFilteredData = (state: { dashboard: DashboardState }) => state.dashboard.filteredData;
export const selectDashboardStatus = (state: { dashboard: DashboardState }) => state.dashboard.status;

export default dashboardSlice.reducer;
