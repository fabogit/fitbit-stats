import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export function ZonesChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const chartColors = useMemo(() => {
    return resolvedTheme === "dark"
      ? ["#94a3b8", "#facc15", "#fb923c", "#f87171"]
      : ["#334155", "#eab308", "#f97316", "#ef4444"];
  }, [resolvedTheme]);

  const chartData = useMemo(() => {
    const totals = filteredData.reduce(
      (acc, curr) => ({
        sedentary: acc.sedentary + (curr.sedentary_minutes || 0),
        light: acc.light + (curr.lightly_active_minutes || 0),
        moderate: acc.moderate + (curr.moderately_active_minutes || 0),
        very: acc.very + (curr.very_active_minutes || 0),
      }),
      { sedentary: 0, light: 0, moderate: 0, very: 0 }
    );

    return [
      { name: "Sedentary", value: totals.sedentary },
      { name: "Light", value: totals.light },
      { name: "Moderate", value: totals.moderate },
      { name: "Very Active", value: totals.very },
    ];
  }, [filteredData]);

  const totalMinutes = chartData.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm flex flex-col h-full">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Activity Zones
        </h3>
        <InfoTooltip
          content={
            <span>
              Total minutes spent in each intensity zone for the selected
              period.
              <br />
              <strong className="text-indigo-500">Insight:</strong> High
              "Sedentary" time can offset workout benefits.
            </span>
          }
        />
      </div>

      <div className="flex-1 min-h-[300px] w-full flex items-center justify-center">
        {totalMinutes > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
                stroke="hsl(var(--card))"
              >
                {chartData.map((_entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={chartColors[index % chartColors.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--popover-foreground))",
                  borderRadius: "var(--radius)",
                }}
                itemStyle={{ color: "hsl(var(--foreground))" }}
                formatter={(
                  value: number | string | Array<number | string>
                ) => {
                  const numValue = Number(value);

                  const displayValue = !isNaN(numValue)
                    ? numValue.toString()
                    : "0";

                  return [displayValue, "Duration"];
                }}
              />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-muted-foreground text-sm flex flex-col items-center">
            <span>No activity data for this period</span>
          </div>
        )}
      </div>
    </div>
  );
}
