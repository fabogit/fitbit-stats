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

interface SleepChartProps {
  syncId?: string;
}

// OPTIMIZATION: Memoize chart to prevent re-renders when parent layout changes (e.g. reordering)
export const SleepChart = memo(function SleepChart({
  syncId,
}: SleepChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <div className="flex items-center mb-6">
        <h3 className="text-lg font-semibold text-card-foreground">
          Sleep Architecture
        </h3>
        <InfoTooltip
          content={
            <span>
              Breakdown of sleep stages.
              <br />
              <strong className="text-indigo-500">Deep:</strong> Physical
              restoration.
              <br />
              <strong className="text-purple-500">REM:</strong> Mental recovery.
              <br />
              <strong className="text-sky-500">Light:</strong> Basic sleep.
              <br />
              <strong className="text-pink-500">Awake:</strong> Disturbances.
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

            <YAxis stroke={axisColor} tick={{ fontSize: 12 }} unit="m" />

            <Tooltip
              cursor={{ fill: "hsl(var(--foreground))", opacity: 0.1 }}
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
              itemStyle={{ fontSize: 12 }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />
            <Bar dataKey="sleep_deep" name="Deep" stackId="a" fill="#4f46e5" />
            <Bar dataKey="sleep_rem" name="REM" stackId="a" fill="#9333ea" />
            <Bar
              dataKey="sleep_light"
              name="Light"
              stackId="a"
              fill="#0ea5e9"
            />
            <Bar
              dataKey="sleep_awake"
              name="Awake"
              stackId="a"
              fill="#db2777"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
