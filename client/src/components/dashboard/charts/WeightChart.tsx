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
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface WeightChartProps {
  syncId?: string;
}

export function WeightChart({ syncId }: WeightChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">
          Weight vs Calories
        </h3>
        <InfoTooltip
          content={
            <span>
              Correlates{" "}
              <strong className="text-yellow-400">Body Weight</strong> (Line)
              with{" "}
              <strong className="text-orange-400">Energy Expenditure</strong>{" "}
              (Area).
              <br />
              <span className="text-slate-400">Insight:</span> Look for lagged
              trends where sustained high calorie burn leads to a drop in weight
              over time.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={filteredData} syncId={syncId}>
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
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

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
