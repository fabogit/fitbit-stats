import { memo } from "react";
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
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface WeightChartProps {
  syncId?: string;
}

// OPTIMIZATION: Memoize chart to prevent re-renders when parent layout changes (e.g. reordering)
export const WeightChart = memo(function WeightChart({
  syncId,
}: WeightChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const weightColor = resolvedTheme === "dark" ? "#facc15" : "#ca8a04"; // Yellow-400 vs Yellow-600
  const caloriesColor = resolvedTheme === "dark" ? "#fb923c" : "#ea580c"; // Orange-400 vs Orange-600

  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Weight vs Calories
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Correlates{" "}
              <strong style={{ color: weightColor }}>Body Weight</strong> (Line)
              with{" "}
              <strong style={{ color: caloriesColor }}>
                Energy Expenditure
              </strong>{" "}
              (Area).
              <br />
              <span className="text-muted-foreground">Insight:</span> Look for
              lagged trends where sustained high calorie burn leads to a drop in
              weight over time.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={filteredData} syncId={syncId}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />

            <YAxis
              yAxisId="left"
              domain={["auto", "auto"]}
              stroke={weightColor}
              tick={{ fontSize: 12 }}
              unit=" kg"
            />

            <YAxis
              yAxisId="right"
              orientation="right"
              stroke={caloriesColor}
              tick={{ fontSize: 12 }}
              unit=" kcal"
            />

            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
              labelStyle={{ color: "hsl(var(--muted-foreground))" }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            <Area
              yAxisId="right"
              type="monotone"
              dataKey="calories_total"
              name="Calories"
              fill={caloriesColor}
              fillOpacity={0.1}
              stroke={caloriesColor}
            />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="weight"
              name="Weight"
              stroke={weightColor}
              strokeWidth={2}
              dot={{ r: 3, fill: weightColor }}
              connectNulls={true}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
