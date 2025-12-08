import { Info } from "lucide-react";

interface InfoTooltipProps {
  content: React.ReactNode;
}

export function InfoTooltip({ content }: InfoTooltipProps) {
  return (
    <div className="relative group inline-flex ml-2 items-center cursor-help">
      <Info className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 transition-colors" />

      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 pointer-events-none">
        {content}

        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
      </div>
    </div>
  );
}
