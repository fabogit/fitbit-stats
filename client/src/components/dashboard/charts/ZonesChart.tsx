import { useMemo, memo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { selectFilteredData } from "@/features/dashboard/dashboardSlice";

export const ZonesChart = memo(function ZonesChart() {
  const filteredData = useAppSelector(selectFilteredData);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  
  const chartColors = useMemo(() => {
    return resolvedTheme === "dark"
      ? ["#94a3b8", "#facc15", "#fb923c", "#f87171"]
      : ["#475569", "#d97706", "#ea580c", "#dc2626"];
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
    ].filter(d => d.value > 0);
  }, [filteredData]);

  const totalMinutes = useMemo(() => chartData.reduce((acc, curr) => acc + curr.value, 0), [chartData]);

  const renderCustomizedLabel = (props: PieLabelRenderProps) => {
    const {
      cx,
      cy,
      midAngle,
      innerRadius,
      outerRadius,
      percent,
    } = props;
    
    if (cx === undefined || cy === undefined || midAngle === undefined || innerRadius === undefined || outerRadius === undefined || percent === undefined) {
      return null;
    }

    const RADIAN = Math.PI / 180;
    const radius = Number(innerRadius) + (Number(outerRadius) - Number(innerRadius)) * 0.5;
    const x = Number(cx) + radius * Math.cos(-Number(midAngle) * RADIAN);
    const y = Number(cy) + radius * Math.sin(-Number(midAngle) * RADIAN);
    
    if (percent < 0.05) return null;

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        className="text-[10px] font-bold pointer-events-none drop-shadow-md"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="bg-card border border-border rounded-xl p-4 md:p-6 shadow-sm flex flex-col h-full">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Activity Zones
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Total minutes spent in each intensity zone for the selected period.<br />
              <strong className="text-indigo-500">Insight:</strong> High "Sedentary" time can offset workout benefits.
            </span>
          }
        />
      </div>

      <div className="flex-1 min-h-[250px] w-full flex items-center justify-center">
        {totalMinutes > 0 ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <PieChart margin={{ top: 0, bottom: 0 }}>
              <Pie
                data={chartData}
                cx="50%"
                cy="45%"
                innerRadius={50}
                outerRadius={85}
                paddingAngle={5}
                dataKey="value"
                stroke="hsl(var(--card))"
                labelLine={false}
                label={renderCustomizedLabel}
              >
                {chartData.map((_entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={chartColors[index % chartColors.length]}
                    className="hover:opacity-80 transition-opacity"
                  />
                ))}
              </Pie>
              <Tooltip
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
                formatter={(value: number | string | readonly (number | string)[] | undefined, name?: number | string) => {
                  const numValue = Number(value);
                  const percentage = ((numValue / totalMinutes) * 100).toFixed(1);
                  return [`${numValue} min (${percentage}%)`, String(name)];
                }}
              />
              <Legend 
                verticalAlign="bottom" 
                align="center" 
                iconType="circle"
                wrapperStyle={{ paddingTop: '20px', fontSize: '11px', fontWeight: 500 }}
              />
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
});
