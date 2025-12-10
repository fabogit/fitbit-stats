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
import { useAppSelector } from "@/store";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface PhysiologyChartProps {
  syncId?: string;
}

export function PhysiologyChart({ syncId }: PhysiologyChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  // --- DATA CLEANING ---
  // Recharts spezza la linea SOLO se il valore è esattamente 'null' o 'undefined'.
  // Se per caso arriva uno '0', la linea tocca il fondo.
  // Qui forziamo: se rmssd è 0 o null, diventa null.
  const cleanData = filteredData.map((d) => ({
    ...d,
    rmssd: d.rmssd && d.rmssd > 0 ? d.rmssd : null,
  }));

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div className="flex items-center mb-6">
        <h3 className="text-lg font-semibold text-slate-100">
          Physiology: HRV & Stress
        </h3>
        <InfoTooltip
          content={
            <span>
              <strong className="text-emerald-400">HRV (Line):</strong> Heart
              Rate Variability (ms).
              <br />
              <span className="text-xs text-slate-400">
                Gaps indicate missing data.
              </span>
              <br />
              <strong className="text-violet-400">
                Stress Score (Area):
              </strong>{" "}
              Higher score = Better handling.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          {/* Usiamo cleanData invece di filteredData */}
          <ComposedChart data={cleanData} syncId={syncId}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />

            {/* Asse SX: HRV */}
            <YAxis
              yAxisId="left"
              stroke="#34d399"
              tick={{ fontSize: 12 }}
              domain={["auto", "auto"]}
              width={40}
            />

            {/* Asse DX: Stress */}
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#a78bfa"
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              width={40}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                borderColor: "#334155",
                color: "#f8fafc",
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            {/* Stress (Area) */}
            <Area
              yAxisId="right"
              type="monotone"
              dataKey="stress_score"
              name="Stress Mngmt Score"
              fill="#8b5cf6"
              fillOpacity={0.15}
              stroke="#8b5cf6"
              connectNulls={false}
            />

            {/* HRV (Line) */}
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="rmssd"
              name="HRV (rMSSD)"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
