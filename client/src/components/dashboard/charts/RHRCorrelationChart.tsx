import { memo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export const RHRCorrelationChart = memo(function RHRCorrelationChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);

  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  // Filter data to only include records with both RHR and Sleep Score
  const chartData = filteredData
    .filter((d) => d.resting_bpm !== null && d.overall_score !== null)
    .map((d) => ({
      rhr: d.resting_bpm,
      sleep: d.overall_score,
      date: d.date,
    }));

  return (
    <div className="bg-card border border-border rounded-xl p-4 md:p-6 shadow-sm h-full flex flex-col">
      <div className="flex items-center mb-4 md:mb-6">
        <h3 className="text-base md:text-lg font-semibold text-card-foreground">
          RHR vs Sleep Quality
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Correlation between <strong>Resting HR</strong> and <strong>Sleep Score</strong>.
              <br />
              Ideally, lower RHR correlates with better sleep.
            </span>
          }
        />
      </div>

      <div className="h-[250px] md:h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%" debounce={100}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} />
            <XAxis
              type="number"
              dataKey="rhr"
              name="RHR"
              unit=" bpm"
              stroke={axisColor}
              domain={['dataMin - 5', 'dataMax + 5']}
              fontSize={12}
              tickFormatter={(val) => Math.round(val).toString()}
            />
            <YAxis
              type="number"
              dataKey="sleep"
              name="Sleep Score"
              unit=""
              stroke={axisColor}
              domain={[40, 100]}
              fontSize={12}
              tickFormatter={(val) => Math.round(val).toString()}
            />
            <ZAxis type="category" dataKey="date" name="Date" />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
            />
            <Scatter name="Days" data={chartData} fill="#f43f5e">
              {chartData.map((_entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={(_entry.sleep ?? 0) > 80 ? "#10b981" : "#f43f5e"} 
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
