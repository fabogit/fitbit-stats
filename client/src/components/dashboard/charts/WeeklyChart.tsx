import { useMemo, memo } from "react";
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
  LabelList,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { parseISO, getDay } from "date-fns";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { selectFilteredData } from "@/features/dashboard/dashboardSlice";

type DayStat = {
  sum: number;
  count: number;
  label: string;
};

interface CustomLabelProps {
  x?: number | string;
  y?: number | string;
  width?: number | string;
  value?: number | string | boolean | null;
}

export const WeeklyChart = memo(function WeeklyChart() {
  const filteredData = useAppSelector(selectFilteredData);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#475569";

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

  const renderCustomLabel = (props: CustomLabelProps) => {
    const { x, y, width, value } = props;
    const numValue = Number(value);
    if (isNaN(numValue) || numValue === 0) return null;
    
    // Position label based on positive/negative value
    const offset = numValue >= 0 ? -15 : 15;
    
    return (
      <text
        x={(Number(x) || 0) + (Number(width) || 0) / 2}
        y={(Number(y) || 0) + offset}
        fill={axisColor}
        textAnchor="middle"
        dominantBaseline="middle"
        className="text-[10px] font-bold"
      >
        {numValue.toFixed(1)}
      </text>
    );
  };

  return (
    <div className="bg-card border border-border rounded-xl p-4 md:p-6 shadow-sm h-full flex flex-col">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Weekly Readiness Pattern
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Average Readiness Score by day of the week.
              <br />
              <strong className="text-emerald-500">Positive:</strong> Generally recovered.
              <br />
              <strong className="text-rose-500">Negative:</strong> Generally tired/stressed.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <BarChart data={chartData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.3}
            />
            <XAxis 
              dataKey="day" 
              stroke={axisColor} 
              tick={{ fontSize: 11, fontWeight: 600 }} 
              axisLine={false}
              tickLine={false}
            />
            <YAxis 
              stroke={axisColor} 
              tick={{ fontSize: 11, fontWeight: 500 }} 
              domain={['auto', 'auto']}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.1 }}
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                padding: '8px 12px',
                borderRadius: '12px',
                border: '1px border border-border',
                boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
              }}
              labelStyle={{ color: 'hsl(var(--muted-foreground))', fontWeight: 600, marginBottom: '4px' }}
              itemStyle={{ color: "hsl(var(--popover-foreground))", fontSize: '12px', fontWeight: 500 }}
              formatter={(value: number | string | readonly (number | string)[] | undefined, name?: number | string) => [Number(value).toFixed(2), String(name ?? "Avg Readiness")]}
            />
            <ReferenceLine y={0} stroke={axisColor} strokeWidth={1} opacity={0.5} />
            <Bar dataKey="avgReadiness" radius={[4, 4, 0, 0]}>
              <LabelList dataKey="avgReadiness" content={renderCustomLabel} />
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.avgReadiness >= 0 ? "#10b981" : "#ef4444"}
                  className="hover:opacity-80 transition-opacity"
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
