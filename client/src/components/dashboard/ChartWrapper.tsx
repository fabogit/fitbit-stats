import type { ReactNode } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChartWrapperProps {
  children: ReactNode;
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst: boolean;
  isLast: boolean;
}

export function ChartWrapper({
  children,
  onMoveUp,
  onMoveDown,
  isFirst,
  isLast,
}: ChartWrapperProps) {
  return (
    <div className="flex gap-4 items-start animate-in fade-in slide-in-from-bottom-2 duration-500">
      {/* Colonna controlli laterale */}
      <div className="flex flex-col gap-2 pt-4 sticky top-4">
        {/* Bottone SU */}
        <button
          onClick={onMoveUp}
          disabled={isFirst}
          className={cn(
            "p-2 rounded-lg border transition-all duration-200",
            isFirst
              ? "border-slate-800 text-slate-700 cursor-not-allowed opacity-50"
              : "border-slate-700 bg-slate-800 text-slate-400 hover:text-indigo-400 hover:border-indigo-500 hover:bg-slate-700 shadow-sm"
          )}
          title="Move Chart Up"
        >
          <ChevronUp className="w-5 h-5" />
        </button>

        {/* Bottone GIÙ */}
        <button
          onClick={onMoveDown}
          disabled={isLast}
          className={cn(
            "p-2 rounded-lg border transition-all duration-200",
            isLast
              ? "border-slate-800 text-slate-700 cursor-not-allowed opacity-50"
              : "border-slate-700 bg-slate-800 text-slate-400 hover:text-indigo-400 hover:border-indigo-500 hover:bg-slate-700 shadow-sm"
          )}
          title="Move Chart Down"
        >
          <ChevronDown className="w-5 h-5" />
        </button>
      </div>

      {/* Il Grafico vero e proprio */}
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
