import { useMemo } from "react";
import { useAppSelector } from "@/store/store";
import { DataTable } from "../datagrid/DataTable";
import { columns } from "../datagrid/columns";
import { calculateStats } from "@/lib/statistics";

export function DataGridView() {
  const { filteredData } = useAppSelector((state) => state.dashboard);

  const stats = useMemo(() => calculateStats(filteredData), [filteredData]);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Detailed Data Log
        </h2>
        <p className="text-muted-foreground text-sm">
          Dynamic Heatmap Table. Colors are relative to the currently filtered
          period (Low/Medium/High 33% split).
        </p>
      </div>

      <DataTable columns={columns} data={filteredData} stats={stats} />
    </div>
  );
}
