import { memo } from "react";
import {
  BarChart,
  Bar,
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

interface EnergyChartProps {
  syncId?: string;
}

// OPTIMIZATION: Memoize chart to prevent re-renders when parent layout changes (e.g. reordering)
export const EnergyChart = memo(function EnergyChart({
  syncId,
}: EnergyChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  const resolvedTheme = useAppSelector(selectResolvedTheme);

  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";
  const bmrColor = resolvedTheme === "dark" ? "#475569" : "#64748b";

  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Daily Energy
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              <strong>BMR (Grey):</strong> Calories burned at rest based on your
              stats.
              <br />
              <strong className="text-amber-500">Active (Orange):</strong>{" "}
              Calories burned purely through movement and exercise.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filteredData} syncId={syncId}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />
            <YAxis stroke={axisColor} tick={{ fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: "hsl(var(--foreground))", opacity: 0.1 }}
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            <Bar dataKey="bmr" name="BMR (Base)" stackId="a" fill={bmrColor} />
            <Bar
              dataKey="active_calories"
              name="Active Burn"
              stackId="a"
              fill="#f59e0b"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
