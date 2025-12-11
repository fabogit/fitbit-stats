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
import { useAppSelector } from "@/store";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface SleepChartProps {
  syncId?: string;
}

export function SleepChart({ syncId }: SleepChartProps) {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div className="flex items-center mb-6">
        <h3 className="text-lg font-semibold text-slate-100">
          Sleep Architecture
        </h3>
        <InfoTooltip
          content={
            <span>
              Breakdown of sleep stages.
              <br />
              <strong className="text-indigo-400">Deep:</strong> Physical
              restoration.
              <br />
              <strong className="text-purple-400">REM:</strong> Mental recovery.
              <br />
              <strong className="text-sky-400">Light:</strong> Basic sleep.
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
              stroke="#334155"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} unit="m" />
            <Tooltip
              cursor={{ fill: "#334155", opacity: 0.2 }}
              contentStyle={{
                backgroundColor: "#1e293b",
                borderColor: "#334155",
                color: "#f8fafc",
              }}
              itemStyle={{ fontSize: 12 }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />
            <Bar
              dataKey="sleep_deep"
              name="Deep"
              stackId="a"
              fill="#4f46e5"
            />{" "}
            {/* Indigo-600 */}
            <Bar
              dataKey="sleep_rem"
              name="REM"
              stackId="a"
              fill="#9333ea"
            />{" "}
            {/* Purple-600 */}
            <Bar
              dataKey="sleep_light"
              name="Light"
              stackId="a"
              fill="#0ea5e9"
            />{" "}
            {/* Sky-500 */}
            <Bar
              dataKey="sleep_awake"
              name="Awake"
              stackId="a"
              fill="#db2777"
            />{" "}
            {/* Pink-600 */}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
