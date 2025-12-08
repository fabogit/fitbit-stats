import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store";

export function WeightChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">
        Weight vs Calories
      </h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={filteredData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />

            {/* Left Axis: Weight */}
            <YAxis
              yAxisId="left"
              domain={["auto", "auto"]}
              stroke="#facc15" // Yellow
              tick={{ fontSize: 12 }}
              unit=" kg"
            />
            {/* Right Axis: Calories */}
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#fb923c" // Orange
              tick={{ fontSize: 12 }}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                borderColor: "#334155",
                color: "#f8fafc",
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Legend />

            <Area
              yAxisId="right"
              type="monotone"
              dataKey="calories_total"
              name="Calories"
              fill="#fb923c"
              fillOpacity={0.1}
              stroke="#fb923c"
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="weight"
              name="Weight"
              stroke="#facc15"
              strokeWidth={2}
              dot={{ r: 3, fill: "#facc15" }}
              connectNulls={true}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
