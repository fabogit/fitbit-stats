import "@tanstack/react-table";
import { RowData } from "@tanstack/react-table";
import { ColumnStats } from "@/lib/statistics";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface TableMeta<TData extends RowData> {
    stats: Record<string, ColumnStats>;
  }
}
