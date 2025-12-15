import type {
  ColumnDef,
  HeaderContext,
  TableMeta,
} from "@tanstack/react-table";
import type { HealthRecord } from "@/types/health";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const f = (val: unknown, dec = 0) => {
  if (typeof val !== "number") return "-";
  return val.toFixed(dec);
};

const getCellColor = (
  val: number | null,
  key: string,
  meta: TableMeta<HealthRecord> | undefined,
  higherIsBetter: boolean = true
) => {
  if (val === null || val === undefined || !meta?.stats?.[key])
    return "text-muted-foreground";

  const stats = meta.stats[key];

  if (higherIsBetter) {
    if (val <= stats.p33) return "text-rose-600 dark:text-rose-400 font-medium";
    if (val >= stats.p66)
      return "text-emerald-600 dark:text-emerald-400 font-medium";
    return "text-amber-600 dark:text-amber-200/80";
  } else {
    if (val <= stats.p33)
      return "text-emerald-600 dark:text-emerald-400 font-medium";
    if (val >= stats.p66) return "text-rose-600 dark:text-rose-400 font-medium";
    return "text-amber-600 dark:text-amber-200/80";
  }
};

const sortableHeader =
  (label: string) =>
  ({ column }: HeaderContext<HealthRecord, unknown>) => {
    return (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="hover:bg-accent h-8 px-2 text-xs font-semibold text-muted-foreground -ml-2"
      >
        {label}
        <ArrowUpDown className="ml-2 h-3 w-3" />
      </Button>
    );
  };

export const columns: ColumnDef<HealthRecord>[] = [
  {
    accessorKey: "date",
    header: sortableHeader("Date"),
    cell: ({ row }) => (
      <div className="font-mono text-xs text-muted-foreground">
        {row.getValue("date")}
      </div>
    ),
  },

  {
    accessorKey: "readiness_raw",
    header: sortableHeader("Readiness"),
    cell: ({ row }) => {
      const val = row.getValue("readiness_raw") as number | null;
      let color = "text-muted-foreground";
      if (val !== null) {
        if (val > 1) color = "text-emerald-600 dark:text-emerald-400 font-bold";
        else if (val < -1) color = "text-rose-600 dark:text-rose-400 font-bold";
        else color = "text-blue-600 dark:text-blue-300";
      }
      return <div className={cn("text-xs", color)}>{f(val, 2)}</div>;
    },
  },

  {
    accessorKey: "resting_bpm",
    header: sortableHeader("RHR"),
    cell: ({ row, table }) => {
      const val = row.getValue("resting_bpm") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "resting_bpm", table.options.meta, false)
          )}
        >
          {f(val)}
        </div>
      );
    },
  },
  {
    accessorKey: "rmssd",
    header: sortableHeader("HRV"),
    cell: ({ row, table }) => {
      const val = row.getValue("rmssd") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "rmssd", table.options.meta, true)
          )}
        >
          {f(val)}
        </div>
      );
    },
  },
  {
    accessorKey: "stress_score",
    header: sortableHeader("Stress"),
    cell: ({ row, table }) => {
      const val = row.getValue("stress_score") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "stress_score", table.options.meta, true)
          )}
        >
          {f(val)}
        </div>
      );
    },
  },
  {
    accessorKey: "spo2_avg",
    header: sortableHeader("SpO2"),
    cell: ({ row, table }) => {
      const val = row.getValue("spo2_avg") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "spo2_avg", table.options.meta, true)
          )}
        >
          {f(val)}%
        </div>
      );
    },
  },
  {
    accessorKey: "overall_score",
    header: sortableHeader("Sleep"),
    cell: ({ row, table }) => {
      const val = row.getValue("overall_score") as number;
      return (
        <div
          className={cn(
            "text-xs font-mono",
            getCellColor(val, "overall_score", table.options.meta, true)
          )}
        >
          {f(val)}
        </div>
      );
    },
  },
  {
    accessorKey: "sleep_deep",
    header: sortableHeader("Deep (m)"),
    cell: ({ row, table }) => {
      const val = row.getValue("sleep_deep") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "sleep_deep", table.options.meta, true)
          )}
        >
          {f(val)}
        </div>
      );
    },
  },
  {
    accessorKey: "calories_total",
    header: sortableHeader("Cals"),
    cell: ({ row, table }) => {
      const val = row.getValue("calories_total") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "calories_total", table.options.meta, true)
          )}
        >
          {parseInt(f(val)).toLocaleString()}
        </div>
      );
    },
  },
  {
    accessorKey: "active_calories",
    header: sortableHeader("Active"),
    cell: ({ row, table }) => {
      const val = row.getValue("active_calories") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "active_calories", table.options.meta, true)
          )}
        >
          {parseInt(f(val)).toLocaleString()}
        </div>
      );
    },
  },
  {
    accessorKey: "intensity_index",
    header: sortableHeader("Intens."),
    cell: ({ row, table }) => {
      const val = row.getValue("intensity_index") as number;
      return (
        <div
          className={cn(
            "text-xs",
            getCellColor(val, "intensity_index", table.options.meta, true)
          )}
        >
          {f(val, 1)}
        </div>
      );
    },
  },
  {
    accessorKey: "weight",
    header: sortableHeader("Weight"),
    cell: ({ row }) => (
      <div className="text-xs text-muted-foreground">
        {f(row.getValue("weight"), 1)}
      </div>
    ),
  },
];
