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
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export function TrendChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">Health Trend</h3>
        <InfoTooltip
          content={
            <span>
              Comparison between your daily{" "}
              <strong className="text-blue-400">Readiness</strong> (Blue) and{" "}
              <strong className="text-rose-500">Resting Heart Rate</strong>{" "}
              (Red).
              <br />
              <span className="text-slate-400">Insight:</span> Ideally, when RHR
              drops, Readiness goes up. A spike in RHR often signals stress or
              illness.
            </span>
          }
        />
      </div>

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
