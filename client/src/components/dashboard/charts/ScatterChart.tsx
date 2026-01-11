import {
  ScatterChart as ReScatter,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { selectResolvedTheme } from "@/store/slices/themeSlice";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    name: string;
    payload: {
      x: number;
      y: number;
      date: string;
      calories_total: number;
      overall_score: number;
    };
  }>;
}

export function ScatterChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const resolvedTheme = useAppSelector(selectResolvedTheme);
  const axisColor = resolvedTheme === "dark" ? "#94a3b8" : "#64748b";

  const scatterData = filteredData
    .filter(
      (d) =>
        d.calories_total > 0 && d.overall_score !== null && d.overall_score > 0
    )
    .map((d) => ({
      x: d.calories_total,
      y: d.overall_score,
      date: d.date,
      calories_total: d.calories_total,
      overall_score: d.overall_score,
    }));

  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-card-foreground">
          Correlation: Activity vs Sleep
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              Each dot represents a single day.
              <br />
              <strong>X:</strong> Calories, <strong>Y:</strong> Sleep Score.
              <br />
              Insight: Does high activity lead to better sleep?
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ReScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis
              type="number"
              dataKey="x"
              name="Calories"
              stroke={axisColor}
              tick={{ fontSize: 12 }}
              label={{
                value: "Calories Burned",
                position: "insideBottom",
                offset: -10,
                fill: axisColor,
              }}
            />

            <YAxis
              type="number"
              dataKey="y"
              name="Sleep Score"
              stroke={axisColor}
              tick={{ fontSize: 12 }}
              domain={[50, 100]}
              label={{
                value: "Sleep Score",
                angle: -90,
                position: "insideLeft",
                fill: axisColor,
              }}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={<CustomTooltip />}
            />
            <Scatter
              name="Days"
              data={scatterData}
              fill="#8b5cf6"
              fillOpacity={0.6}
            />
          </ReScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Alias */
const ReScatterChart = ReScatter;

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-popover border border-border p-2 rounded shadow-lg text-xs text-popover-foreground">
        <p className="font-bold mb-1 text-muted-foreground">{data.date}</p>
        <p>
          Calories:{" "}
          <span className="text-orange-500 font-mono">
            {data.calories_total.toFixed(0)}
          </span>
        </p>
        <p>
          Sleep Score:{" "}
          <span className="text-indigo-500 font-mono">
            {data.overall_score}
          </span>
        </p>
      </div>
    );
  }
  return null;
};
