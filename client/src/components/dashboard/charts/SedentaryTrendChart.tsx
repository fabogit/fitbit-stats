import { memo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export const SedentaryTrendChart = memo(function SedentaryTrendChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);

  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  const chartData = filteredData.map((d) => ({
    date: d.date,
    sedentary: d.sedentary_minutes || 0,
    active: (d.lightly_active_minutes || 0) + (d.moderately_active_minutes || 0) + (d.very_active_minutes || 0),
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-4 md:p-6 shadow-sm h-full flex flex-col">
      <div className="flex items-center mb-4 md:mb-6">
        <h3 className="text-base md:text-lg font-semibold text-card-foreground">
          Activity Balance
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Comparison between <strong>Active Minutes</strong> and <strong>Sedentary Minutes</strong>.
              <br />
              Try to keep sedentary time below your daily average.
            </span>
          }
        />
      </div>

      <div className="h-[250px] md:h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%" debounce={100}>
          <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorSedentary" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
            <XAxis dataKey="date" hide />
            <YAxis stroke={axisColor} fontSize={12} unit="m" />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
            />
            <Area
              type="monotone"
              dataKey="sedentary"
              stroke="#64748b"
              fillOpacity={1}
              fill="url(#colorSedentary)"
              name="Sedentary"
            />
            <Area
              type="monotone"
              dataKey="active"
              stroke="#10b981"
              fill="transparent"
              name="Active Total"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
