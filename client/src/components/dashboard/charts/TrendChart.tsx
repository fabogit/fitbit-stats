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
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface TrendChartProps {
  syncId?: string;
}

export function TrendChart({ syncId }: TrendChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Health Trend
        </h3>
        <InfoTooltip
          content={
            <span>
              Comparison between your daily{" "}
              <strong className="text-blue-500">Readiness</strong> (Blue) and{" "}
              <strong className="text-rose-500">Resting Heart Rate</strong>{" "}
              (Red).
              <br />
              <span className="text-muted-foreground">Insight:</span> Ideally,
              when RHR drops, Readiness goes up.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData} syncId={syncId}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />

            <XAxis dataKey="date" hide />

            <YAxis
              yAxisId="left"
              domain={[-4, 4]}
              stroke={axisColor}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={["auto", "auto"]}
              stroke={axisColor}
              tick={{ fontSize: 12 }}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
              itemStyle={{ fontSize: 12 }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            <Line
              yAxisId="left"
              type="monotone"
              dataKey="readiness_raw"
              name="Readiness (Z)"
              stroke="#3b82f6"
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
