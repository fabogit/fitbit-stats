import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { parseISO, getDay } from "date-fns";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

type DayStat = {
  sum: number;
  count: number;
  label: string;
};

export function WeeklyChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  const chartData = useMemo(() => {
    const daysAcc: Record<number, DayStat> = {
      0: { sum: 0, count: 0, label: "Sun" },
      1: { sum: 0, count: 0, label: "Mon" },
      2: { sum: 0, count: 0, label: "Tue" },
      3: { sum: 0, count: 0, label: "Wed" },
      4: { sum: 0, count: 0, label: "Thu" },
      5: { sum: 0, count: 0, label: "Fri" },
      6: { sum: 0, count: 0, label: "Sat" },
    };

    filteredData.forEach((d) => {
      if (d.readiness_raw !== null) {
        const dateObj = parseISO(d.date);
        const dayIndex = getDay(dateObj);
        if (daysAcc[dayIndex]) {
          daysAcc[dayIndex].sum += d.readiness_raw;
          daysAcc[dayIndex].count += 1;
        }
      }
    });

    const sortOrder = [1, 2, 3, 4, 5, 6, 0];

    return sortOrder.map((index) => {
      const dayData = daysAcc[index];
      return {
        day: dayData.label,
        avgReadiness: dayData.count > 0 ? dayData.sum / dayData.count : 0,
      };
    });
  }, [filteredData]);

  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Weekly Readiness Pattern
        </h3>
        <InfoTooltip
          content={
            <span>
              Average Readiness Score by day of the week.
              <br />
              <strong className="text-emerald-500">Positive:</strong> Generally
              recovered.
              <br />
              <strong className="text-rose-500">Negative:</strong> Generally
              tired/stressed.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis dataKey="day" stroke={axisColor} tick={{ fontSize: 12 }} />
            <YAxis stroke={axisColor} tick={{ fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.2 }}
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
              formatter={(value: number | string | Array<number | string> | undefined) => {
                const numValue = Number(value);

                const displayValue = !isNaN(numValue)
                  ? numValue.toFixed(1)
                  : "0";

                return [displayValue, "Avg Score"];
              }}
            />
            <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" />
            <Bar dataKey="avgReadiness">
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.avgReadiness >= 0 ? "#34d399" : "#f43f5e"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
