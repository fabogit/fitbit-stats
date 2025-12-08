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
import { InfoTooltip } from "@/components/ui/InfoTooltip"; // <--- Import

export function EnergyChart() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">Daily Energy</h3>
        <InfoTooltip
          content={
            <span>
              <strong>BMR (Grey):</strong> Calories burned at rest based on your
              stats.
              <br />
              <strong className="text-amber-500">Active (Orange):</strong>{" "}
              Calories burned purely through movement and exercise.
            </span>
          }
        />
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filteredData}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.5}
            />
            <XAxis dataKey="date" hide />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <Tooltip
              cursor={{ fill: "#334155", opacity: 0.2 }}
              contentStyle={{
                backgroundColor: "#1e293b",
                borderColor: "#334155",
                color: "#f8fafc",
              }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            <Bar
              dataKey="bmr"
              name="BMR (Base)"
              stackId="a"
              fill="#64748b" // Slate-500
            />
            <Bar
              dataKey="active_calories"
              name="Active Burn"
              stackId="a"
              fill="#f59e0b" // Amber-500
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
