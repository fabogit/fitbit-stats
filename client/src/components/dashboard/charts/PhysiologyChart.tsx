import { memo } from "react";
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useAppSelector } from "@/store/store";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface PhysiologyChartProps {
  syncId?: string;
}

// OPTIMIZATION: Memoize chart to prevent re-renders when parent layout changes (e.g. reordering)
export const PhysiologyChart = memo(function PhysiologyChart({
  syncId,
}: PhysiologyChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  const cleanData = filteredData.map((d) => ({
    ...d,
    rmssd: d.rmssd && d.rmssd > 0 ? d.rmssd : null,
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
      <div className="flex items-center mb-6">
        <h3 className="text-lg font-semibold text-card-foreground">
          Physiology: HRV & Stress
        </h3>
        <InfoTooltip
          side="bottom"
          content={
            <span>
              <strong className="text-emerald-500">HRV (Line):</strong> Heart
              Rate Variability (ms).
              <br />
              <span className="text-xs text-muted-foreground">
                Gaps indicate missing data.
              </span>
              <br />
              <strong className="text-violet-500">
                Stress Score (Area):
              </strong>{" "}
              Higher score = Better handling.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={cleanData} syncId={syncId}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />

            <YAxis
              yAxisId="left"
              stroke="#10b981"
              tick={{ fontSize: 12 }}
              domain={["auto", "auto"]}
              width={40}
            />

            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#8b5cf6"
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              width={40}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: "var(--radius)",
              }}
              labelStyle={{ color: "hsl(var(--muted-foreground))" }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            <Area
              yAxisId="right"
              type="monotone"
              dataKey="stress_score"
              name="Stress Mngmt Score"
              fill="#8b5cf6"
              fillOpacity={0.2}
              stroke="#8b5cf6"
            />

            <Line
              yAxisId="left"
              type="monotone"
              dataKey="rmssd"
              name="HRV (rMSSD)"
              stroke="#10b981"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});
