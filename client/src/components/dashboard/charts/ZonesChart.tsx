import { useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

const COLORS = ["#334155", "#eab308", "#f97316", "#ef4444"]; // Slate, Yellow, Orange, Red

export function ZonesChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col h-full">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">Activity Zones</h3>
        <InfoTooltip
          content={
            <span>
              Total minutes spent in each intensity zone for the selected
              period.
              <br />
              <strong className="text-indigo-400">Insight:</strong> High
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
                stroke="none"
              >
                {chartData.map((_entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  borderColor: "#334155",
                  color: "#f8fafc",
                }}
                itemStyle={{ color: "#fff" }}
                formatter={(value: number) => [
                  `${value.toLocaleString()} min`,
                  "Duration",
                ]}
              />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-slate-500 text-sm flex flex-col items-center">
            <span>No activity data for this period</span>
          </div>
        )}
      </div>
    </div>
  );
}
