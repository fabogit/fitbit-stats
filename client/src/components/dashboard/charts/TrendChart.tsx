import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store";

export function TrendChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">
        Health Trend
      </h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />
            {/* Left Axis: Readiness */}
            <YAxis
              yAxisId="left"
              domain={[-4, 4]}
              stroke="#60a5fa" // Blue
              tick={{ fontSize: 12 }}
            />
            {/* Right Axis: RHR */}
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={["auto", "auto"]}
              stroke="#f43f5e" // Red
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                borderColor: "#334155",
                color: "#f8fafc",
              }}
              itemStyle={{ fontSize: 12 }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            <Line
              yAxisId="left"
              type="monotone"
              dataKey="readiness_raw"
              name="Readiness (Z)"
              stroke="#60a5fa"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="resting_bpm"
              name="RHR (bpm)"
              stroke="#f43f5e"
              strokeDasharray="5 5"
              strokeWidth={1}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
