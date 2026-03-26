import { memo, useMemo } from "react";
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

export const SleepCompositionChart = memo(function SleepCompositionChart() {
  const filteredData = useAppSelector((state) => state.dashboard.filteredData);
  const resolvedTheme = useAppSelector(selectResolvedTheme);

  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  // Data mapping: ensure we have minutes for each stage
  const chartData = useMemo(() => {
    return filteredData.map((d) => ({
      date: d.date,
      Deep: d.sleep_deep || 0,
      REM: d.sleep_rem || 0,
      Light: d.sleep_light || 0,
      Awake: d.sleep_awake || 0,
    }));
  }, [filteredData]);

  return (
    <div className="bg-card border border-border rounded-xl p-4 md:p-6 shadow-sm h-full flex flex-col">
      <div className="flex items-center mb-4 md:mb-6">
        <h3 className="text-base md:text-lg font-semibold text-card-foreground">
          Sleep Composition
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Breakdown of sleep stages for each night.
              <br />
              <strong className="text-indigo-500">Deep + REM:</strong> Restorative stages.
            </span>
          }
        />
      </div>

      <div className="h-[250px] md:h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%" debounce={100}>
          <BarChart
            data={chartData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />
            <YAxis
              stroke={axisColor}
              tick={{ fontSize: 12 }}
              label={{
                value: "Minutes",
                angle: -90,
                position: "insideLeft",
                offset: 0,
                fontSize: 12,
                fill: axisColor,
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
            />
            <Legend
              wrapperStyle={{ paddingTop: "10px", fontSize: "12px" }}
              iconType="circle"
            />
            {/* Awake - Top */}
            <Bar dataKey="Awake" stackId="a" fill="#f43f5e" radius={[2, 2, 0, 0]} />
            {/* Light */}
            <Bar dataKey="Light" stackId="a" fill="#38bdf8" />
            {/* REM - Restorative */}
            <Bar dataKey="REM" stackId="a" fill="#818cf8" />
            {/* Deep - Most Restorative - Bottom */}
            <Bar dataKey="Deep" stackId="a" fill="#4f46e5" radius={[0, 0, 2, 2]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
