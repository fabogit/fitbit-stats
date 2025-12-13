import { useState } from "react";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ColumnStats } from "@/lib/statistics";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  stats: Record<string, ColumnStats>;
}

const coreRowModel = getCoreRowModel();
const paginationRowModel = getPaginationRowModel();
const sortedRowModel = getSortedRowModel();

export function DataTable<TData, TValue>({
  columns,
  data,
  stats,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 15,
  });

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: coreRowModel,
    getPaginationRowModel: paginationRowModel,
    getSortedRowModel: sortedRowModel,
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    state: {
      sorting,
      pagination,
    },
    meta: {
      stats: stats,
    },
  });

  return (
    <div className="space-y-4">
      {/* --- TABLE CONTAINER --- */}
      <div className="rounded-lg border border-slate-800 bg-slate-900 overflow-hidden shadow-sm">
        <Table>
          <TableHeader className="bg-slate-950">
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="border-slate-800 hover:bg-slate-900"
              >
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead
                      key={header.id}
                      className="text-slate-400 h-10 px-4 font-medium"
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className="border-slate-800 hover:bg-slate-800/50 transition-colors h-10"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="py-2 px-4">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-slate-500"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* --- PAGINATION CONTROLS --- */}
      <div className="flex items-center justify-between px-2">
        {/* Page Size Selector */}
        <div className="flex items-center space-x-2">
          <p className="text-xs font-medium text-slate-400">Rows</p>
          <Select
            value={`${table.getState().pagination.pageSize}`}
            onValueChange={(value) => {
              table.setPageSize(Number(value));
            }}
          >
            <SelectTrigger className="h-8 w-[70px] bg-slate-900 border-slate-700 text-slate-300 text-xs">
              <SelectValue placeholder={table.getState().pagination.pageSize} />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-slate-300">
              {[15, 30, 60, 100].map((pageSize) => (
                <SelectItem key={pageSize} value={`${pageSize}`}>
                  {pageSize}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Page Navigation */}
        <div className="flex items-center space-x-2">
          <div className="flex w-[100px] items-center justify-center text-xs font-medium text-slate-400">
            Page {table.getState().pagination.pageIndex + 1} of{" "}
            {table.getPageCount()}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="h-8 w-8 p-0 border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
          >
            {"<"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="h-8 w-8 p-0 border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
          >
            {">"}
          </Button>
        </div>
      </div>
    </div>
  );
}
