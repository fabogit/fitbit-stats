import {
  createSlice,
  createAsyncThunk,
  type PayloadAction,
} from "@reduxjs/toolkit";
import type { HealthRecord, DateRange } from "@/types/health";
import { subMonths, parseISO, format } from "date-fns";

interface DashboardState {
  data: HealthRecord[];
  filteredData: HealthRecord[];
  dateRange: DateRange | null;
  status: "idle" | "loading" | "succeeded" | "failed";
  error: string | null;
}

const initialState: DashboardState = {
  data: [],
  filteredData: [],
  dateRange: null,
  status: "idle",
  error: null,
};

export const fetchHealthData = createAsyncThunk(
  "dashboard/fetchHealthData",
  async () => {
    const response = await fetch("/dashboard_data.json");
    if (!response.ok) throw new Error("Failed to load dashboard data");
    return (await response.json()) as HealthRecord[];
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

export const { setDateRange, resetFilter } = dashboardSlice.actions;
export default dashboardSlice.reducer;
